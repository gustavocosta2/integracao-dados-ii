"""Simulador de topologia industrial e leituras de sensores IoT."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from iot_platform.models import (
    Machine,
    Part,
    ProductionLine,
    ReadingStatus,
    Sensor,
    SensorReading,
)


@dataclass(frozen=True)
class FactoryTopology:
    """Conjunto completo de entidades da planta industrial simulada."""

    lines: list[ProductionLine]
    parts: list[Part]
    machines: list[Machine]
    sensors: list[Sensor]


def default_factory_topology() -> FactoryTopology:
    """Retorna uma planta industrial modelo com linhas, máquinas, peças e sensores."""
    lines = [
        ProductionLine(line_id="L1", name="Linha 1 - Usinagem", sector="Producao"),
        ProductionLine(line_id="L2", name="Linha 2 - Montagem", sector="Acabamento"),
    ]

    parts = [
        Part(part_id="P1", name="Rolamento Principal", supplier="SKF", criticality="alta"),
        Part(part_id="P2", name="Compressor Hidraulico", supplier="Bosch", criticality="alta"),
        Part(part_id="P3", name="Correia Transmissao", supplier="Gates", criticality="media"),
        Part(part_id="P4", name="Valvula Solenoide", supplier="Festo", criticality="alta"),
    ]

    machines = [
        Machine(
            machine_id="M1",
            line_id="L1",
            name="Torno CNC 01",
            machine_type="usinagem",
            criticality="alta",
            specs={"potencia_kw": 18.5, "fabricante": "Romi", "ano": 2023},
            part_ids=["P1", "P3"],
            depends_on_machine_ids=[],
        ),
        Machine(
            machine_id="M2",
            line_id="L1",
            name="Prensa Hidraulica 02",
            machine_type="conformacao",
            criticality="alta",
            specs={"pressao_max_bar": 250, "fabricante": "Schuler", "ano": 2022},
            part_ids=["P2", "P4"],
            depends_on_machine_ids=["M1"],
        ),
        Machine(
            machine_id="M3",
            line_id="L2",
            name="Robo Solda 01",
            machine_type="soldagem",
            criticality="media",
            specs={"eixos": 6, "fabricante": "KUKA", "ano": 2024},
            part_ids=["P1"],
            depends_on_machine_ids=["M2"],
        ),
        Machine(
            machine_id="M4",
            line_id="L2",
            name="Estacao Teste Final",
            machine_type="inspecao",
            criticality="alta",
            specs={"ciclo_seg": 12, "fabricante": "Siemens", "ano": 2024},
            part_ids=["P4"],
            depends_on_machine_ids=["M3"],
        ),
    ]

    sensors = [
        Sensor(
            sensor_id="S1",
            machine_id="M1",
            machine_name="Torno CNC 01",
            line_id="L1",
            sensor_type="temperatura",
            unit="C",
            min_normal=40.0,
            max_normal=75.0,
        ),
        Sensor(
            sensor_id="S2",
            machine_id="M1",
            machine_name="Torno CNC 01",
            line_id="L1",
            sensor_type="vibracao",
            unit="mm/s",
            min_normal=0.5,
            max_normal=4.5,
        ),
        Sensor(
            sensor_id="S3",
            machine_id="M2",
            machine_name="Prensa Hidraulica 02",
            line_id="L1",
            sensor_type="pressao",
            unit="bar",
            min_normal=120.0,
            max_normal=210.0,
        ),
        Sensor(
            sensor_id="S4",
            machine_id="M2",
            machine_name="Prensa Hidraulica 02",
            line_id="L1",
            sensor_type="temperatura",
            unit="C",
            min_normal=45.0,
            max_normal=80.0,
        ),
        Sensor(
            sensor_id="S5",
            machine_id="M3",
            machine_name="Robo Solda 01",
            line_id="L2",
            sensor_type="temperatura",
            unit="C",
            min_normal=35.0,
            max_normal=70.0,
        ),
        Sensor(
            sensor_id="S6",
            machine_id="M4",
            machine_name="Estacao Teste Final",
            line_id="L2",
            sensor_type="vibracao",
            unit="mm/s",
            min_normal=0.2,
            max_normal=3.0,
        ),
    ]

    return FactoryTopology(lines=lines, parts=parts, machines=machines, sensors=sensors)


def classify_reading(value: float, sensor: Sensor) -> ReadingStatus:
    """Classifica uma leitura em ok, warning ou critical segundo a faixa do sensor."""
    span = sensor.max_normal - sensor.min_normal
    warning_upper = sensor.max_normal + 0.15 * span
    warning_lower = max(0.0, sensor.min_normal - 0.15 * span)

    if sensor.min_normal <= value <= sensor.max_normal:
        return "ok"
    if warning_lower <= value <= warning_upper:
        return "warning"
    return "critical"


def build_deterministic_batch_id(base_time: datetime, seed: int, count_per_sensor: int) -> str:
    """Gera identificador determinístico de lote para suportar reprocessamento idempotente."""
    raw = f"{base_time.astimezone(UTC).isoformat()}|{seed}|{count_per_sensor}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def generate_readings_batch(
    sensors: list[Sensor],
    count_per_sensor: int = 5,
    base_time: datetime | None = None,
    seed: int = 42,
    anomaly_rate: float = 0.15,
    batch_id: str | None = None,
) -> list[SensorReading]:
    """Gera um lote reproduzível de leituras com anomalias ocasionais."""
    if count_per_sensor <= 0:
        raise ValueError("count_per_sensor deve ser maior que zero.")
    if not 0.0 <= anomaly_rate <= 1.0:
        raise ValueError("anomaly_rate deve estar entre 0.0 e 1.0.")

    start_ts = (base_time or datetime.now(UTC)).astimezone(UTC)
    resolved_batch_id = batch_id or build_deterministic_batch_id(start_ts, seed, count_per_sensor)
    rng = random.Random(seed)
    readings: list[SensorReading] = []

    for step in range(count_per_sensor):
        event_ts = start_ts + timedelta(seconds=step * 10)
        for sensor in sensors:
            span = sensor.max_normal - sensor.min_normal
            if rng.random() < anomaly_rate:
                # Gera pico acima do limite para simular anomalia operacional
                value = sensor.max_normal + rng.uniform(0.05 * span, 0.45 * span)
            else:
                value = rng.uniform(sensor.min_normal, sensor.max_normal)

            status = classify_reading(value, sensor)
            reading_id = f"{resolved_batch_id}_{sensor.sensor_id}_{step:04d}"
            readings.append(
                SensorReading(
                    reading_id=reading_id,
                    sensor_id=sensor.sensor_id,
                    machine_id=sensor.machine_id,
                    line_id=sensor.line_id,
                    sensor_type=sensor.sensor_type,
                    value=value,
                    unit=sensor.unit,
                    status=status,
                    event_ts=event_ts,
                    batch_id=resolved_batch_id,
                )
            )

    return readings
