"""Testes de integração ponta a ponta contra os containers Docker da Entrega 1."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

from iot_platform.config import Settings
from iot_platform.run_ingestion import run_pipeline
from iot_platform.storage.bronze_minio import BronzeMinioRepository
from iot_platform.storage.cassandra_repo import CassandraTimeSeriesRepository
from iot_platform.storage.mongo_repo import MongoCatalogRepository
from iot_platform.storage.neo4j_repo import Neo4jTopologyRepository
from iot_platform.storage.redis_repo import RedisStateRepository

RUN_INTEGRATION = os.getenv("RUN_INTEGRATION_TESTS", "0") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Defina RUN_INTEGRATION_TESTS=1 com o Docker Compose ativo para rodar integracao.",
)


def test_full_ingestion_and_idempotency() -> None:
    batch_id = f"it_{int(datetime.now(UTC).timestamp())}"

    first = run_pipeline(count_per_sensor=3, seed=7, anomaly_rate=0.35, batch_id=batch_id)
    assert first["readings_count"] == 18
    assert first["mongo_new_batch"] is True
    assert first["redis_new_batch"] is True
    assert first["mongo_explain_stage"] == "IXSCAN"
    assert first["cassandra_rows"] == 18

    # Reprocessar exatamente o mesmo batch_id nao deve duplicar contadores no Mongo nem no Redis
    second = run_pipeline(count_per_sensor=3, seed=7, anomaly_rate=0.35, batch_id=batch_id)
    assert second["mongo_new_batch"] is False
    assert second["redis_new_batch"] is False
    assert second["bronze_key"] == first["bronze_key"]

    settings = Settings()

    bronze = BronzeMinioRepository(
        endpoint_url=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket,
    )
    records = bronze.read_jsonl(first["bronze_key"])
    assert len(records) == 18
    assert records[0]["_ingestion"]["batch_id"] == batch_id

    redis_repo = RedisStateRepository(settings.redis_host, settings.redis_port, settings.redis_db)
    try:
        latest = redis_repo.get_latest_sensor_state("S1")
        assert latest["batch_id"] == batch_id
        assert redis_repo.client.ttl("sensor:latest:S1") > 0
    finally:
        redis_repo.close()

    cassandra_repo = CassandraTimeSeriesRepository(
        settings.cassandra_hosts, settings.cassandra_port, settings.cassandra_keyspace
    )
    try:
        rows = cassandra_repo.get_sensor_readings("S1", datetime.now(UTC).date(), limit=10)
        assert any(r["batch_id"] == batch_id for r in rows)
    finally:
        cassandra_repo.close()

    neo4j_repo = Neo4jTopologyRepository(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        line_sensors = neo4j_repo.find_sensors_by_line("L1")
        assert len(line_sensors) == 4
        impact = neo4j_repo.find_impacted_machines_by_part("P1")
        assert len(impact) >= 1
    finally:
        neo4j_repo.close()

    mongo_repo = MongoCatalogRepository(settings.mongo_uri, settings.mongo_db)
    try:
        machine_m1 = mongo_repo.db.machines.find_one({"machine_id": "M1"})
        assert machine_m1 is not None
        assert len(machine_m1["recent_alerts"]) <= 10
    finally:
        mongo_repo.close()
