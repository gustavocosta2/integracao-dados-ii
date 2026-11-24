"""Configurações centralizadas da plataforma carregadas via variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Parâmetros de conexão com Object Storage e bancos NoSQL."""

    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ROOT_USER", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "iot-datalake")

    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db: str = os.getenv("MONGO_DB", "iot_catalog")

    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))

    cassandra_hosts: tuple[str, ...] = tuple(
        h.strip() for h in os.getenv("CASSANDRA_HOSTS", "localhost").split(",") if h.strip()
    )
    cassandra_port: int = int(os.getenv("CASSANDRA_PORT", "9042"))
    cassandra_keyspace: str = os.getenv("CASSANDRA_KEYSPACE", "iot_timeseries")

    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "iot_neo4j_pass")
