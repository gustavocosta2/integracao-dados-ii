"""Repositório de estado rápido e contadores no Redis com TTL."""

from __future__ import annotations

import logging

import redis

from iot_platform.models import SensorReading

logger = logging.getLogger(__name__)


class RedisStateRepository:
    """Mantém última leitura por sensor, contadores diários e alertas ativos com expiração."""

    def __init__(self, host: str, port: int, db: int = 0) -> None:
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    def close(self) -> None:
        self.client.close()

    def update_from_readings(
        self,
        readings: list[SensorReading],
        batch_id: str,
        latest_ttl_seconds: int = 3600,
        alert_ttl_seconds: int = 1800,
    ) -> bool:
        """Atualiza estado rápido e contadores garantindo idempotência por batch_id."""
        marker_key = f"batch:processed:redis:{batch_id}"
        already_processed = not self.client.set(marker_key, "1", nx=True, ex=86400)

        pipe = self.client.pipeline()
        for reading in readings:
            latest_key = f"sensor:latest:{reading.sensor_id}"
            pipe.hset(
                latest_key,
                mapping={
                    "machine_id": reading.machine_id,
                    "line_id": reading.line_id,
                    "sensor_type": reading.sensor_type,
                    "value": str(reading.value),
                    "unit": reading.unit,
                    "status": reading.status,
                    "event_ts": reading.event_ts.isoformat(),
                    "batch_id": reading.batch_id,
                },
            )
            pipe.expire(latest_key, latest_ttl_seconds)

            if not already_processed:
                day_str = reading.event_ts.strftime("%Y%m%d")
                count_key = f"sensor:count:{reading.sensor_id}:{day_str}"
                pipe.incr(count_key)
                pipe.expire(count_key, 86400)

            if reading.status in {"warning", "critical"}:
                alert_key = f"alert:active:{reading.machine_id}"
                pipe.hset(
                    alert_key,
                    mapping={
                        "sensor_id": reading.sensor_id,
                        "sensor_type": reading.sensor_type,
                        "value": str(reading.value),
                        "status": reading.status,
                        "event_ts": reading.event_ts.isoformat(),
                    },
                )
                pipe.expire(alert_key, alert_ttl_seconds)

        pipe.execute()
        logger.info("Redis atualizado com %d leituras (novo lote=%s).", len(readings), not already_processed)
        return not already_processed

    def get_latest_sensor_state(self, sensor_id: str) -> dict[str, str]:
        """Retorna a última leitura armazenada para um sensor."""
        return self.client.hgetall(f"sensor:latest:{sensor_id}")
