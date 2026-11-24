# ADR 0003: Modelagem Orientada a Consultas, Índices e Ciclo de Vida NoSQL

- **Status:** Aceito
- **Data:** 2026-11-23
- **Entrega:** Entrega 1 — Fundação

## Contexto

Bancos NoSQL exigem modelagem orientada às consultas (*query-first design*) para evitar gargalos clássicos como *collection scans*, documentos crescendo sem limite (*Unbounded Arrays*), partições desbalanceadas no Cassandra e travessias explosivas em grafos.

## Decisão

Aplicar padrões explícitos em cada banco:
1. **MongoDB:**
   - **Subset + Computed Pattern:** embutir em `machines` apenas os últimos 10 alertas (`recent_alerts`) e contadores pré-calculados (`metrics_summary`), mantendo o histórico completo fora do documento.
   - **Extended Reference:** embutir `machine_name` e `line_id` nos documentos de `sensors` para resolver listagens por sensor em uma única leitura.
   - **Índices compostos ESR:** criar índices cobrindo filtros reais (`{line_id: 1, status: 1, updated_at: -1}` e `{machine_id: 1, sensor_type: 1, status: 1}`) e validar planos de execução (`IXSCAN` em vez de `COLLSCAN`).
2. **Redis:**
   - Chaves prefixadas por domínio (`sensor:latest:<id>`, `sensor:count:<id>:<YYYYMMDD>`, `alert:active:<machine_id>`) sempre com **TTL explícito** (`EX`) para evitar vazamento de memória.
3. **Cassandra:**
   - Chave primária `PRIMARY KEY ((sensor_id, bucket_date), event_ts)` com `CLUSTERING ORDER BY (event_ts DESC)` — o `bucket_date` evita partições gigantes por sensor ao longo do tempo e permite consultas rápidas às leituras recentes de um sensor.
   - TTL padrão de 30 dias para retenção operacional quente.
4. **Neo4j:**
   - Constraints de unicidade (`id`) em `Linha`, `Maquina`, `Sensor` e `Peca`, e consultas de dependência sempre com profundidade limitada (`*1..3`).

## Alternativas Consideradas

- **Normalização estrita no MongoDB com `$lookup` em todas as leituras:** traria mentalidade relacional para o NoSQL, multiplicando leituras e latência.
- **Partition key apenas por `sensor_id` no Cassandra:** causaria crescimento indefinido da partição física com o acúmulo de meses de leitura por segundo.

## Consequências

- **Positivas:** leituras previsíveis em uma única consulta/lookup, uso controlado de RAM/disco e proteção contra crescimento ilimitado de documentos e partições.
- **Negativas / Trade-offs:** atualização do nome de uma máquina exige propagar a alteração para os documentos de `sensors` que usam *Extended Reference*, trade-off aceito dado que cadastros de máquinas mudam raramente.
