"""Repositório da camada Bronze utilizando MinIO (API compatível com S3)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from iot_platform.models import SensorReading

logger = logging.getLogger(__name__)


def build_bronze_object_key(batch_ts: datetime, batch_id: str) -> str:
    """Constrói chave particionada por ano/mes/dia/hora na camada Bronze."""
    utc_ts = batch_ts.astimezone(UTC)
    return (
        f"bronze/sensors/"
        f"year={utc_ts:%Y}/month={utc_ts:%m}/day={utc_ts:%d}/hour={utc_ts:%H}/"
        f"readings_{batch_id}.jsonl"
    )


class BronzeMinioRepository:
    """Persiste lotes brutos de sensores no MinIO preservando o payload original."""

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
    ) -> None:
        self.bucket = bucket
        self.client: BaseClient = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        )

    def ensure_bucket(self) -> None:
        """Cria o bucket de datalake caso ainda não exista."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)
            logger.info("Bucket '%s' criado no MinIO.", self.bucket)

    def write_readings_batch(self, readings: list[SensorReading], batch_id: str) -> str:
        """Grava leituras brutas em formato JSONL de forma idempotente por batch_id."""
        if not readings:
            raise ValueError("Nao e possivel gravar um lote vazio na camada Bronze.")

        self.ensure_bucket()
        ingested_at = datetime.now(UTC).isoformat()
        batch_ts = readings[0].event_ts
        object_key = build_bronze_object_key(batch_ts, batch_id)

        lines = []
        for reading in readings:
            payload = reading.model_dump(mode="json")
            payload["_ingestion"] = {
                "batch_id": batch_id,
                "ingested_at": ingested_at,
                "source": "iot-simulator",
            }
            lines.append(json.dumps(payload, ensure_ascii=False))

        body = ("\n".join(lines) + "\n").encode("utf-8")
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=body,
            ContentType="application/x-ndjson",
        )
        logger.info("Lote '%s' (%d registros) gravado em s3://%s/%s.", batch_id, len(readings), self.bucket, object_key)
        return object_key

    def list_objects(self, prefix: str = "bronze/sensors/") -> list[str]:
        """Lista chaves existentes sob um prefixo da camada Bronze."""
        response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        return [item["Key"] for item in response.get("Contents", [])]

    def read_jsonl(self, object_key: str) -> list[dict]:
        """Lê e decodifica um arquivo JSONL da camada Bronze."""
        response = self.client.get_object(Bucket=self.bucket, Key=object_key)
        raw = response["Body"].read().decode("utf-8")
        return [json.loads(line) for line in raw.splitlines() if line.strip()]
