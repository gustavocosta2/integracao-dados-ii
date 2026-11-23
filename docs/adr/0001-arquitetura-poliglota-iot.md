# ADR 0001: Adoção de Persistência Poliglota na Plataforma IoT

- **Status:** Aceito
- **Data:** 2026-11-23
- **Entrega:** Entrega 1 — Fundação

## Contexto

A plataforma precisa atender padrões de acesso bastante distintos para um ecossistema industrial com linhas de produção, máquinas, peças e sensores IoT:
1. Cadastro flexível de equipamentos com atributos heterogêneos por tipo de máquina.
2. Leitura de última medição e contadores em tempo real com latência mínima.
3. Escrita intensiva de séries temporais por sensor ordenadas no tempo.
4. Consultas de impacto e dependência multi-nível entre linhas, máquinas e peças.
5. Histórico bruto preservado e barato para auditoria, reprocessamento e analytics (Entregas 2 e 3).

## Decisão

Adotar **Persistência Poliglota** utilizando quatro bancos NoSQL complementares somados ao Object Storage:
- **MongoDB (Document Store):** catálogo de linhas, máquinas e sensores.
- **Redis (Key-Value):** último estado conhecido por sensor, contadores e alertas ativos com TTL.
- **Cassandra (Wide-Column):** séries temporais de leituras por `(sensor_id, bucket_date)`.
- **Neo4j (Graph):** topologia da fábrica e travessias de impacto/dependência.
- **MinIO (Object Storage):** camada Bronze para armazenamento bruto em escala.

## Alternativas Consideradas

- **Banco Relacional Único (ex.: PostgreSQL):** simplificaria a operação inicial, mas exigiria `JOIN`s recursivos custosos para dependências em múltiplos níveis, esquema rígido para metadados variáveis de sensores e escalabilidade horizontal limitada para alta taxa de escrita IoT.
- **Apenas MongoDB para tudo:** suportaria o catálogo e leituras simples, porém teria pior eficiência que Redis em estado efêmero sub-milissegundo, menos naturalidade que Neo4j para travessias em grafo e maior custo para séries temporais massivas do que Cassandra + Parquet/MinIO.

## Consequências

- **Positivas:** cada padrão de consulta crítico roda no modelo de dados ideal, evitando anti-padrões (como *JOINs* recursivos artificiais ou arrays ilimitados).
- **Negativas / Trade-offs:** maior complexidade operacional (5 serviços em Docker) e necessidade de manter consistência eventual entre catálogo, cache e série temporal na camada de aplicação/ingestão.
