# Integração de Dados II — Projeto Integrador (Plataforma IoT)

Repositório do Projeto Integrador da disciplina **Integração de Dados II** (Ciência de Dados e Inteligência Artificial — PUC Minas, 2026/1).

## Arquitetura e Entregas

- Documentação completa da arquitetura: [docs/arquitetura.md](docs/arquitetura.md)
- Registros de Decisão Arquitetural (ADRs):
  - [ADR 0001 — Persistência Poliglota](docs/adr/0001-arquitetura-poliglota-iot.md)
  - [ADR 0002 — MinIO e Camada Bronze](docs/adr/0002-object-storage-minio-e-camada-bronze.md)
  - [ADR 0003 — Modelagem NoSQL e Índices](docs/adr/0003-modelagem-nosql-e-indices.md)

### Entregas do Cronograma
1. **Entrega 1 — Fundação (Semana 5):** infraestrutura Docker (`MinIO`, `MongoDB`, `Redis`, `Cassandra`, `Neo4j`), simulador de sensores IoT, modelagem NoSQL orientada a consultas e ingestão idempotente na camada Bronze.
2. **Entrega 2 — Pipeline (Semana 10):** jobs Spark (`Bronze → Silver → Gold`), DAGs Airflow e dashboard básico.
3. **Entrega 3 — Integração Final (Semana 15):** pipeline streaming, alertas de anomalias, testes de qualidade, documentação completa e demonstração ao vivo.

## Pré-requisitos

- Docker e Docker Compose
- Python 3.11+

## Como Rodar a Entrega 1 (Passo a Passo)

1. **Copie o arquivo de variáveis de ambiente:**
   ```bash
   cp .env.example .env
   ```

2. **Suba os serviços no Docker:**
   ```bash
   docker compose up -d
   docker compose ps
   ```
   Aguarde até que todos os serviços (`id2-minio`, `id2-mongodb`, `id2-redis`, `id2-neo4j`, `id2-cassandra`) estejam rodando e saudáveis.

3. **Crie o ambiente virtual Python e instale as dependências:**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

4. **Execute o simulador e a ingestão poliglota + Bronze:**
   ```bash
   python -m iot_platform.run_ingestion --count 5 --seed 42 --anomaly-rate 0.2
   ```

5. **Interfaces locais para inspeção visual:**
   - **MinIO Console (Camada Bronze):** http://localhost:9001 (`minioadmin` / `minioadmin`)
   - **Neo4j Browser (Topologia em Grafo):** http://localhost:7474 (`neo4j` / `iot_neo4j_pass`)

## Testes e Qualidade

- **Testes unitários e de regressão (sem precisar do Docker):**
  ```bash
  pytest tests/test_simulator.py tests/test_bronze_and_models.py -v
  ```
- **Testes de integração ponta a ponta (com `docker compose up -d` ativo):**
  ```bash
  RUN_INTEGRATION_TESTS=1 pytest tests/test_integration.py -v
  ```
- **Lint e padronização:**
  ```bash
  ruff check src tests
  ```

## Fluxo Git do Repositório

Consulte as regras obrigatórias de branches, commits com emojis, PRs em português brasileiro e testes de regressão em [AGENTS.md](AGENTS.md).
