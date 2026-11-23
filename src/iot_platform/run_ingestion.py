"""CLI principal da Entrega 1: gera leituras IoT e popula Bronze (S3) + NoSQL."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime

from iot_platform.config import Settings
from iot_platform.simulator import default_factory_topology, generate_readings_batch
from iot_platform.storage.bronze_minio import BronzeMinioRepository
from iot_platform.storage.cassandra_repo import CassandraTimeSeriesRepository
from iot_platform.storage.mongo_repo import MongoCatalogRepository
from iot_platform.storage.neo4j_repo import Neo4jTopologyRepository
from iot_platform.storage.redis_repo import RedisStateRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("iot_platform.pipeline")


def run_pipeline(
    count_per_sensor: int = 5,
    seed: int = 42,
    anomaly_rate: float = 0.2,
    batch_id: str | None = None,
) -> dict:
    """Executa um ciclo completo de geração e persistência poliglota + Bronze."""
    settings = Settings()
    topology = default_factory_topology()
    readings = generate_readings_batch(
        sensors=topology.sensors,
        count_per_sensor=count_per_sensor,
        base_time=datetime.now(UTC),
        seed=seed,
        anomaly_rate=anomaly_rate,
        batch_id=batch_id,
    )
    resolved_batch_id = readings[0].batch_id
    logger.info(
        "Lote gerado: batch_id=%s sensores=%d leituras=%d",
        resolved_batch_id,
        len(topology.sensors),
        len(readings),
    )

    # 1. Camada Bronze no Object Storage S3-compatível
    bronze_repo = BronzeMinioRepository(
        endpoint_url=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket,
    )
    bronze_key = bronze_repo.write_readings_batch(readings, batch_id=resolved_batch_id)

    # 2. Catálogo operacional no MongoDB
    mongo_repo = MongoCatalogRepository(uri=settings.mongo_uri, db_name=settings.mongo_db)
    try:
        mongo_repo.upsert_topology(topology)
        mongo_is_new_batch = mongo_repo.record_readings_summary(readings, batch_id=resolved_batch_id)
        explain_info = mongo_repo.explain_sensors_by_machine("M1")
        winning_stage = (
            explain_info.get("queryPlanner", {})
            .get("winningPlan", {})
            .get("inputStage", {})
            .get("stage")
            or explain_info.get("queryPlanner", {}).get("winningPlan", {}).get("stage")
        )
        logger.info("MongoDB explain stage para busca por machine_id: %s", winning_stage)
    finally:
        mongo_repo.close()

    # 3. Estado rápido com TTL no Redis
    redis_repo = RedisStateRepository(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
    )
    try:
        redis_is_new_batch = redis_repo.update_from_readings(readings, batch_id=resolved_batch_id)
    finally:
        redis_repo.close()

    # 4. Série temporal no Cassandra
    cassandra_repo = CassandraTimeSeriesRepository(
        hosts=settings.cassandra_hosts,
        port=settings.cassandra_port,
        keyspace=settings.cassandra_keyspace,
    )
    try:
        cassandra_repo.ensure_schema()
        cassandra_rows = cassandra_repo.insert_readings(readings)
    finally:
        cassandra_repo.close()

    # 5. Topologia e impacto em grafo no Neo4j
    neo4j_repo = Neo4jTopologyRepository(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )
    try:
        neo4j_repo.sync_topology(topology)
        alerts_created = neo4j_repo.record_alerts(readings)
        impact_p1 = neo4j_repo.find_impacted_machines_by_part("P1")
        logger.info("Neo4j impacto da peca P1: %s", impact_p1)
    finally:
        neo4j_repo.close()

    return {
        "batch_id": resolved_batch_id,
        "readings_count": len(readings),
        "bronze_key": bronze_key,
        "mongo_new_batch": mongo_is_new_batch,
        "mongo_explain_stage": winning_stage,
        "redis_new_batch": redis_is_new_batch,
        "cassandra_rows": cassandra_rows,
        "neo4j_alerts": alerts_created,
        "neo4j_impact_p1": impact_p1,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Executa ingestao IoT (Entrega 1 - Fundacao).")
    parser.add_argument("--count", type=int, default=5, help="Leituras por sensor no lote.")
    parser.add_argument("--seed", type=int, default=42, help="Semente para reproducibilidade.")
    parser.add_argument("--anomaly-rate", type=float, default=0.2, help="Taxa de anomalias (0..1).")
    parser.add_argument("--batch-id", type=str, default=None, help="Identificador explicito do lote.")
    args = parser.parse_args(argv)

    summary = run_pipeline(
        count_per_sensor=args.count,
        seed=args.seed,
        anomaly_rate=args.anomaly_rate,
        batch_id=args.batch_id,
    )
    logger.info("Execucao concluida com sucesso: %s", summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
