"""Testes unitários de particionamento Bronze e regras do simulador."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from iot_platform.simulator import default_factory_topology, generate_readings_batch
from iot_platform.storage.bronze_minio import build_bronze_object_key


def test_build_bronze_object_key_converts_timezone_to_utc() -> None:
    brt = timezone(timedelta(hours=-3))
    ts = datetime(2026, 11, 23, 22, 30, 0, tzinfo=brt)  # 01:30 UTC do dia 24
    key = build_bronze_object_key(ts, batch_id="abc123")
    assert key == "bronze/sensors/year=2026/month=11/day=24/hour=01/readings_abc123.jsonl"


def test_invalid_simulator_parameters_raise_value_error() -> None:
    sensors = default_factory_topology().sensors
    with pytest.raises(ValueError):
        generate_readings_batch(sensors, count_per_sensor=0)
    with pytest.raises(ValueError):
        generate_readings_batch(sensors, anomaly_rate=1.5)
