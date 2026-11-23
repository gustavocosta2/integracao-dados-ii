"""Modelos de domínio e validação de schema da plataforma IoT."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ReadingStatus = Literal["ok", "warning", "critical"]


class ProductionLine(BaseModel):
    """Linha de produção industrial."""

    line_id: str
    name: str
    sector: str


class Part(BaseModel):
    """Peça crítica utilizada pelas máquinas."""

    part_id: str
    name: str
    supplier: str
    criticality: Literal["baixa", "media", "alta"]


class Machine(BaseModel):
    """Máquina industrial monitorada por sensores."""

    machine_id: str
    line_id: str
    name: str
    machine_type: str
    criticality: Literal["baixa", "media", "alta"]
    status: Literal["operacional", "manutencao", "alerta"] = "operacional"
    specs: dict[str, Any] = Field(default_factory=dict)
    part_ids: list[str] = Field(default_factory=list)
    depends_on_machine_ids: list[str] = Field(default_factory=list)


class Sensor(BaseModel):
    """Sensor acoplado a uma máquina industrial."""

    sensor_id: str
    machine_id: str
    machine_name: str
    line_id: str
    sensor_type: Literal["temperatura", "vibracao", "pressao"]
    unit: str
    min_normal: float
    max_normal: float
    status: Literal["ativo", "inativo"] = "ativo"


class SensorReading(BaseModel):
    """Leitura pontual emitida por um sensor."""

    reading_id: str
    sensor_id: str
    machine_id: str
    line_id: str
    sensor_type: Literal["temperatura", "vibracao", "pressao"]
    value: float
    unit: str
    status: ReadingStatus
    event_ts: datetime
    batch_id: str

    @field_validator("value")
    @classmethod
    def validate_finite_value(cls, v: float) -> float:
        """Rejeita valores NaN ou infinitos na leitura do sensor."""
        if not math.isfinite(v):
            raise ValueError("Valor da leitura do sensor deve ser um número finito.")
        return round(v, 3)

    @field_validator("event_ts")
    @classmethod
    def ensure_utc_timestamp(cls, ts: datetime) -> datetime:
        """Garante timestamp com fuso horário UTC."""
        if ts.tzinfo is None:
            return ts.replace(tzinfo=UTC)
        return ts.astimezone(UTC)
