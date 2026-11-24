"""Repositório de séries temporais no Apache Cassandra."""

from __future__ import annotations

import logging
from datetime import date

from cassandra.cluster import Cluster
from cassandra.policies import DCAwareRoundRobinPolicy

from iot_platform.models import SensorReading

logger = logging.getLogger(__name__)


class CassandraTimeSeriesRepository:
    """Persiste séries temporais particionadas por (sensor_id, bucket_date) com TTL."""

    def __init__(self, hosts: tuple[str, ...], port: int, keyspace: str) -> None:
        self.keyspace = keyspace
        self.cluster = Cluster(
            contact_points=list(hosts),
            port=port,
            protocol_version=5,
            load_balancing_policy=DCAwareRoundRobinPolicy(local_dc="dc1"),
        )
        self.session = self.cluster.connect()
        self._insert_stmt = None

    def close(self) -> None:
        self.cluster.shutdown()

    def ensure_schema(self) -> None:
        """Cria keyspace e tabela de séries temporais de forma idempotente."""
        self.session.execute(
            f"""
            CREATE KEYSPACE IF NOT EXISTS {self.keyspace}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
            """
        )
        self.session.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.keyspace}.sensor_readings_by_day (
                sensor_id text,
                bucket_date date,
                event_ts timestamp,
                machine_id text,
                line_id text,
                sensor_type text,
                value double,
                unit text,
                status text,
                batch_id text,
                PRIMARY KEY ((sensor_id, bucket_date), event_ts)
            ) WITH CLUSTERING ORDER BY (event_ts DESC)
              AND default_time_to_live = 2592000
            """
        )
        self._insert_stmt = self.session.prepare(
            f"""
            INSERT INTO {self.keyspace}.sensor_readings_by_day (
                sensor_id, bucket_date, event_ts, machine_id, line_id,
                sensor_type, value, unit, status, batch_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        )

    def insert_readings(self, readings: list[SensorReading]) -> int:
        """Grava leituras em série temporal (upserts idempotentes pela PK)."""
        if self._insert_stmt is None:
            self.ensure_schema()

        for reading in readings:
            bucket_day = reading.event_ts.date()
            self.session.execute(
                self._insert_stmt,
                (
                    reading.sensor_id,
                    bucket_day,
                    reading.event_ts,
                    reading.machine_id,
                    reading.line_id,
                    reading.sensor_type,
                    reading.value,
                    reading.unit,
                    reading.status,
                    reading.batch_id,
                ),
            )
        logger.info("Cassandra recebeu %d registros de serie temporal.", len(readings))
        return len(readings)

    def get_sensor_readings(self, sensor_id: str, bucket_date: date, limit: int = 20) -> list[dict]:
        """Consulta leituras mais recentes de um sensor em um dia específico."""
        rows = self.session.execute(
            f"""
            SELECT sensor_id, bucket_date, event_ts, machine_id, value, status, batch_id
            FROM {self.keyspace}.sensor_readings_by_day
            WHERE sensor_id = %s AND bucket_date = %s
            LIMIT %s
            """,
            (sensor_id, bucket_date, limit),
        )
        return [
            {
                "sensor_id": row.sensor_id,
                "bucket_date": str(row.bucket_date),
                "event_ts": row.event_ts.isoformat(),
                "machine_id": row.machine_id,
                "value": row.value,
                "status": row.status,
                "batch_id": row.batch_id,
            }
            for row in rows
        ]
