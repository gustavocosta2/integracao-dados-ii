# ADR 0002: MinIO como Object Storage Local e Organização da Camada Bronze

- **Status:** Aceito
- **Data:** 2026-11-23
- **Entrega:** Entrega 1 — Fundação

## Contexto

Para evoluir a plataforma nas Entregas 2 e 3 rumo a um Data Lakehouse (com Spark, arquitetura Medalhão Bronze/Silver/Gold e formato de tabela aberto), precisamos de um armazenamento de objetos compatível com a API S3 rodando localmente em Docker sem custos de nuvem. Além disso, precisamos garantir que os dados brutos dos sensores nunca sejam perdidos ou alterados na ingestão inicial (paradigma ELT).

## Decisão

1. Utilizar **MinIO** em container Docker como Object Storage compatível com Amazon S3 (`s3://iot-datalake`).
2. Organizar a camada **Bronze** com particionamento temporal estilo Hive (`bronze/sensors/year=YYYY/month=MM/day=DD/hour=HH/readings_<batch_id>.jsonl`), preservando o payload bruto das leituras somado apenas a metadados técnicos (`batch_id`, `ingested_at`, `source`).
3. Utilizar identificador determinístico (`batch_id`) no nome do objeto para tornar a ingestão de lote re-executável e idempotente.

## Alternativas Consideradas

- **Sistema de arquivos local (`file://`):** mais simples, mas não reproduz a semântica de buckets, chaves S3 e integração nativa usada por Spark, Iceberg/Delta e engines MPP em nuvem.
- **Já gravar em Parquet/Iceberg direto na Entrega 1:** adiantaria parte da Entrega 2, porém acoplaria o simulador ao Spark desde a captura inicial e dificultaria preservar exatamente o payload bruto original para auditoria e reprocessamento.

## Consequências

- **Positivas:** desacopla captura de transformação (ELT), permite reprocessar qualquer janela horária sem perder dados brutos (inclusive leituras anômalas) e mantém compatibilidade direta com `boto3`, Spark e DuckDB nas próximas entregas.
- **Negativas / Trade-offs:** arquivos JSON Lines individuais na Bronze são menos compactos que Parquet; na Entrega 2 o job Bronze → Silver fará a conversão colunar, limpeza e compactação em formato de tabela aberto.
