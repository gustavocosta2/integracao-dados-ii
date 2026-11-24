"""Testes unitários do simulador e validação de modelos IoT."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from iot_platform.models import SensorReading
from iot_platform.simulator import (
    classify_reading,
    default_factory_topology,
    generate_readings_batch,
)


def test_default_topology_consistency() -> None:
    topology = default_factory_topology()
    assert len(topology.lines) == 2
    assert len(topology.machines) == 4
    assert len(topology.sensors) == 6
    machine_ids = {m.machine_id for m in topology.machines}
    for sensor in topology.sensors:
        assert sensor.machine_id in machine_ids


def test_generate_readings_is_deterministic() -> None:
    topology = default_factory_topology()
    fixed_ts = datetime(2026, 11, 23, 14, 0, 0, tzinfo=UTC)

    batch_a = generate_readings_batch(
        topology.sensors, count_per_sensor=4, base_time=fixed_ts, seed=123, anomaly_rate=0.25
    )
    batch_b = generate_readings_batch(
        topology.sensors, count_per_sensor=4, base_time=fixed_ts, seed=123, anomaly_rate=0.25
    )

    assert len(batch_a) == 24
    assert batch_a == batch_b
    assert any(r.status in {"warning", "critical"} for r in batch_a)


def test_classify_reading_boundaries() -> None:
    sensor = default_factory_topology().sensors[0]  # temperatura: 40..75
    assert classify_reading(60.0, sensor) == "ok"
    assert classify_reading(77.0, sensor) == "warning"
    assert classify_reading(95.0, sensor) == "critical"


def test_regression_reject_non_finite_reading_value() -> None:
    """Teste de regressão: leituras NaN/infinitas não podem passar na validação do schema."""
    with pytest.raises(ValueError, match="finito"):
        SensorReading(
            reading_id="r1",
            sensor_id="S1",
            machine_id="M1",
            line_id="L1",
            sensor_type="temperatura",
            value=math.nan,
            unit="C",
            status="ok",
            event_ts=datetime(2026, 11, 23, 14, 0, tzinfo=UTC),
            batch_id="b1",
        )


def test_regression_naive_timestamp_normalized_to_utc() -> None:
    """Teste de regressão: timestamps sem timezone são normalizados para UTC."""
    reading = SensorReading(
        reading_id="r2",
        sensor_id="S1",
        machine_id="M1",
        line_id="L1",
        sensor_type="temperatura",
        value=55.1234,
        unit="C",
        status="ok",
        event_ts=datetime(2026, 11, 23, 14, 0),
        batch_id="b1",
    )
    assert reading.event_ts.tzinfo == UTC
    assert reading.value == 55.123
