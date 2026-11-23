"""Repositório de catálogo operacional no MongoDB com padrões query-first e índices ESR."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient

from iot_platform.models import SensorReading
from iot_platform.simulator import FactoryTopology

logger = logging.getLogger(__name__)


class MongoCatalogRepository:
    """Gerencia coleções machines, sensors e controle de idempotência no MongoDB."""

    def __init__(self, uri: str, db_name: str) -> None:
        self.client: MongoClient = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]

    def close(self) -> None:
        self.client.close()

    def ensure_indexes(self) -> None:
        """Cria índices únicos e compostos seguindo a regra ESR (Equality, Sort, Range)."""
        self.db.machines.create_index([("machine_id", ASCENDING)], unique=True, name="ux_machine_id")
        self.db.machines.create_index(
            [("line_id", ASCENDING), ("status", ASCENDING), ("updated_at", DESCENDING)],
            name="ix_machines_line_status_updated",
        )

        self.db.sensors.create_index([("sensor_id", ASCENDING)], unique=True, name="ux_sensor_id")
        self.db.sensors.create_index(
            [("machine_id", ASCENDING), ("sensor_type", ASCENDING), ("status", ASCENDING)],
            name="ix_sensors_machine_type_status",
        )

    def upsert_topology(self, topology: FactoryTopology) -> None:
        """Insere ou atualiza máquinas (Subset/Computed) e sensores (Extended Reference)."""
        self.ensure_indexes()
        now = datetime.now(UTC)

        for machine in topology.machines:
            self.db.machines.update_one(
                {"machine_id": machine.machine_id},
                {
                    "$set": {
                        "line_id": machine.line_id,
                        "name": machine.name,
                        "machine_type": machine.machine_type,
                        "criticality": machine.criticality,
                        "specs": machine.specs,
                        "part_ids": machine.part_ids,
                        "updated_at": now,
                    },
                    "$setOnInsert": {
                        "status": machine.status,
                        "recent_alerts": [],
                        "metrics_summary": {
                            "total_readings": 0,
                            "anomaly_count": 0,
                            "last_reading_at": None,
                        },
                    },
                },
                upsert=True,
            )

        for sensor in topology.sensors:
            # Extended Reference: embute machine_name e line_id para evitar $lookup em leituras
            self.db.sensors.update_one(
                {"sensor_id": sensor.sensor_id},
                {
                    "$set": {
                        "machine_id": sensor.machine_id,
                        "machine_name": sensor.machine_name,
                        "line_id": sensor.line_id,
                        "sensor_type": sensor.sensor_type,
                        "unit": sensor.unit,
                        "limits": {
                            "min_normal": sensor.min_normal,
                            "max_normal": sensor.max_normal,
                        },
                        "status": sensor.status,
                        "updated_at": now,
                    }
                },
                upsert=True,
            )

        logger.info(
            "Catalogo MongoDB sincronizado (%d maquinas, %d sensores).",
            len(topology.machines),
            len(topology.sensors),
        )

    def record_readings_summary(self, readings: list[SensorReading], batch_id: str) -> bool:
        """Atualiza métricas pré-computadas e Subset de alertas de forma idempotente."""
        marker_id = f"mongo:{batch_id}"
        if self.db.ingestion_state.find_one({"_id": marker_id}):
            logger.info("Lote '%s' ja contabilizado no MongoDB; ignorando duplicidade.", batch_id)
            return False

        by_machine: dict[str, dict[str, Any]] = {}
        for reading in readings:
            entry = by_machine.setdefault(
                reading.machine_id,
                {"total": 0, "anomalies": 0, "alerts": [], "last_ts": reading.event_ts},
            )
            entry["total"] += 1
            entry["last_ts"] = max(entry["last_ts"], reading.event_ts)
            if reading.status in {"warning", "critical"}:
                entry["anomalies"] += 1
                entry["alerts"].append(
                    {
                        "reading_id": reading.reading_id,
                        "sensor_id": reading.sensor_id,
                        "sensor_type": reading.sensor_type,
                        "value": reading.value,
                        "status": reading.status,
                        "event_ts": reading.event_ts,
                    }
                )

        for machine_id, info in by_machine.items():
            update_doc: dict[str, Any] = {
                "$inc": {
                    "metrics_summary.total_readings": info["total"],
                    "metrics_summary.anomaly_count": info["anomalies"],
                },
                "$set": {
                    "metrics_summary.last_reading_at": info["last_ts"],
                    "status": "alerta" if info["anomalies"] > 0 else "operacional",
                    "updated_at": datetime.now(UTC),
                },
            }
            if info["alerts"]:
                # Subset Pattern: limita array a 10 alertas recentes (evita Unbounded Arrays)
                update_doc["$push"] = {
                    "recent_alerts": {
                        "$each": info["alerts"][-10:],
                        "$slice": -10,
                    }
                }
            self.db.machines.update_one({"machine_id": machine_id}, update_doc)

        self.db.ingestion_state.insert_one(
            {"_id": marker_id, "batch_id": batch_id, "processed_at": datetime.now(UTC)}
        )
        return True

    def explain_sensors_by_machine(self, machine_id: str) -> dict[str, Any]:
        """Executa explain('executionStats') para comprovar uso de índice (IXSCAN)."""
        return self.db.sensors.find({"machine_id": machine_id}).explain()
