"""Repositório de topologia industrial e análise de impacto no Neo4j."""

from __future__ import annotations

import logging

from neo4j import GraphDatabase

from iot_platform.models import SensorReading
from iot_platform.simulator import FactoryTopology

logger = logging.getLogger(__name__)


class Neo4jTopologyRepository:
    """Mantém o grafo Linha -> Maquina -> Sensor / Peca / Alerta no Neo4j."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def ensure_constraints(self) -> None:
        """Cria constraints de unicidade evitando nós duplicados."""
        queries = [
            "CREATE CONSTRAINT linha_id IF NOT EXISTS FOR (l:Linha) REQUIRE l.id IS UNIQUE",
            "CREATE CONSTRAINT maquina_id IF NOT EXISTS FOR (m:Maquina) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT sensor_id IF NOT EXISTS FOR (s:Sensor) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT peca_id IF NOT EXISTS FOR (p:Peca) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT alerta_id IF NOT EXISTS FOR (a:Alerta) REQUIRE a.id IS UNIQUE",
        ]
        with self.driver.session() as session:
            for query in queries:
                session.run(query)

    def sync_topology(self, topology: FactoryTopology) -> None:
        """Sincroniza topologia completa de forma idempotente via MERGE."""
        self.ensure_constraints()
        with self.driver.session() as session:
            for line in topology.lines:
                session.run(
                    "MERGE (l:Linha {id: $id}) SET l.nome = $nome, l.setor = $setor",
                    id=line.line_id,
                    nome=line.name,
                    setor=line.sector,
                )

            for part in topology.parts:
                session.run(
                    "MERGE (p:Peca {id: $id}) SET p.nome = $nome, p.fornecedor = $fornecedor, p.criticidade = $crit",
                    id=part.part_id,
                    nome=part.name,
                    fornecedor=part.supplier,
                    crit=part.criticality,
                )

            for machine in topology.machines:
                session.run(
                    """
                    MATCH (l:Linha {id: $line_id})
                    MERGE (m:Maquina {id: $id})
                    SET m.nome = $nome, m.tipo = $tipo, m.criticidade = $crit
                    MERGE (l)-[:CONTEM]->(m)
                    """,
                    line_id=machine.line_id,
                    id=machine.machine_id,
                    nome=machine.name,
                    tipo=machine.machine_type,
                    crit=machine.criticality,
                )
                for part_id in machine.part_ids:
                    session.run(
                        """
                        MATCH (m:Maquina {id: $machine_id})
                        MATCH (p:Peca {id: $part_id})
                        MERGE (m)-[:USA]->(p)
                        """,
                        machine_id=machine.machine_id,
                        part_id=part_id,
                    )

            for machine in topology.machines:
                for upstream_id in machine.depends_on_machine_ids:
                    session.run(
                        """
                        MATCH (m:Maquina {id: $machine_id})
                        MATCH (u:Maquina {id: $upstream_id})
                        MERGE (m)-[:DEPENDE_DE]->(u)
                        """,
                        machine_id=machine.machine_id,
                        upstream_id=upstream_id,
                    )

            for sensor in topology.sensors:
                session.run(
                    """
                    MATCH (m:Maquina {id: $machine_id})
                    MERGE (s:Sensor {id: $id})
                    SET s.tipo = $tipo, s.unidade = $unidade
                    MERGE (m)-[:TEM_SENSOR]->(s)
                    """,
                    machine_id=sensor.machine_id,
                    id=sensor.sensor_id,
                    tipo=sensor.sensor_type,
                    unidade=sensor.unit,
                )

        logger.info("Grafo Neo4j sincronizado com sucesso.")

    def record_alerts(self, readings: list[SensorReading]) -> int:
        """Cria nós de alerta ligados ao sensor para leituras warning/critical."""
        anomalies = [r for r in readings if r.status in {"warning", "critical"}]
        if not anomalies:
            return 0

        with self.driver.session() as session:
            for item in anomalies:
                session.run(
                    """
                    MATCH (s:Sensor {id: $sensor_id})
                    MERGE (a:Alerta {id: $reading_id})
                    SET a.status = $status, a.valor = $valor, a.event_ts = $event_ts
                    MERGE (s)-[:GEROU]->(a)
                    """,
                    sensor_id=item.sensor_id,
                    reading_id=item.reading_id,
                    status=item.status,
                    valor=item.value,
                    event_ts=item.event_ts.isoformat(),
                )
        return len(anomalies)

    def find_sensors_by_line(self, line_id: str) -> list[dict]:
        """Lista todos os sensores pertencentes a uma linha de produção."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (:Linha {id: $line_id})-[:CONTEM]->(m:Maquina)-[:TEM_SENSOR]->(s:Sensor)
                RETURN m.id AS maquina_id, m.nome AS maquina, s.id AS sensor_id, s.tipo AS tipo
                ORDER BY m.id, s.id
                """,
                line_id=line_id,
            )
            return [record.data() for record in result]

    def find_impacted_machines_by_part(self, part_id: str) -> list[dict]:
        """Descobre máquinas direta ou indiretamente impactadas (até 3 níveis) pela falha de uma peça."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Peca {id: $part_id})<-[:USA]-(origem:Maquina)
                OPTIONAL MATCH path = (afetada:Maquina)-[:DEPENDE_DE*1..3]->(origem)
                RETURN origem.id AS maquina_origem,
                       collect(DISTINCT afetada.id) AS maquinas_dependentes
                """,
                part_id=part_id,
            )
            return [record.data() for record in result]
