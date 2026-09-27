# Scalable Data Integration for Data Centers

A simple, extensible base project for integrating data across a data
center — pulling telemetry/operational data from multiple sources
(databases, APIs, log/metric files), transforming it into a
consistent shape, and loading it into one or more sinks (a file, a
database, or a data warehouse) — built to scale from a laptop to many
cores/nodes.

## Architecture

```
Sources (parallel)        Transform chain           Sinks
┌───────────────┐         ┌───────────────┐      ┌───────────────┐
│ DatabaseConn  │──┐      │ validate      │      │ FileLoader    │
│ APIConnector  │──┼─────▶│ type_cast     │─────▶│ DatabaseLoader│
│ FileConnector │──┘      │ enrich        │      │ ...           │
└───────────────┘         └───────────────┘      └───────────────┘
   (ThreadPoolExecutor, max_workers configurable)
```

* **Connectors** (`data_integration/connectors/`) extract records from
  a source. Each implements `connect()` / `extract()` / `close()`.
* **Transformers** (`data_integration/transformers/`) apply a chain of
  per-record transformations (validation, type casting, field mapping,
  enrichment). Any transformer can drop a record by returning `None`.
* **Loaders** (`data_integration/loaders/`) batch-write transformed
  records to one or more destinations, with retry + backoff.
* **Pipeline** (`data_integration/pipeline.py`) wires it all together:
  each configured source runs in its own worker thread (I/O-bound
  extraction scales well here), records flow through the shared
  transform chain, and are flushed to every sink in fixed-size
  batches.

Everything is **config-driven** (`config.yaml`) and **pluggable** — add
a new connector/transformer/loader type by subclassing the relevant
base class and registering it (see `register_connector`,
`register_transformer`, `register_loader`).

## Scaling this base project

- `max_workers` in `config.yaml` controls how many sources are pulled
  concurrently — set this near your core count / expected source count.
- `batch_size` controls how many records accumulate before a write,
  trading memory for fewer, larger I/O calls to the sink.
- Extraction uses a thread pool (I/O-bound). For CPU-heavy transforms,
  swap in a `ProcessPoolExecutor` in `pipeline.py`, or run multiple
  pipeline instances (one per node) against disjoint source configs,
  writing to a shared warehouse sink.
- Retries with exponential backoff on every sink write mean a
  transient failure on one node/source doesn't abort the whole run.
- Because sources are mocked automatically when no real connection
  details are given, you can develop/scale-test the orchestration
  logic before any real infrastructure is wired up.

## Getting started

```bash
pip install -r requirements.txt

# Runs immediately using built-in mock data (no DB/API/files needed)
python main.py --config config.yaml

# Check the output
cat output/integrated_data.jsonl
```

Run the smoke test:

```bash
python test_pipeline.py
```

## Wiring up real infrastructure

Edit `config.yaml` and uncomment/fill in the relevant options, e.g.:

```yaml
sources:
  - name: server_metrics_db
    type: database
    options:
      connection_string: "postgresql://user:pass@db-host:5432/metrics"
      query: "SELECT * FROM server_metrics WHERE ts > now() - interval '1 hour'"
```

Then install the optional extras: `pip install sqlalchemy psycopg2-binary requests`.

## Project layout

```
scalable-data-integration/
├── config.yaml                     # pipeline wiring: sources, transforms, sinks
├── main.py                         # CLI entry point
├── requirements.txt
├── test_pipeline.py                # end-to-end smoke test (mock mode)
└── data_integration/
    ├── config.py                   # YAML -> dataclass config loader
    ├── pipeline.py                 # orchestrator (parallel extract/transform/load)
    ├── connectors/
    │   ├── base.py
    │   ├── database_connector.py
    │   ├── api_connector.py
    │   └── file_connector.py
    ├── transformers/
    │   ├── base.py
    │   └── standard_transformers.py
    └── loaders/
        ├── base.py
        └── standard_loaders.py
```

## Extending

Add a new source type in three steps:

```python
# 1. data_integration/connectors/kafka_connector.py
class KafkaConnector(BaseConnector):
    def connect(self): ...
    def extract(self): ...

# 2. Register it
from data_integration.connectors import register_connector
register_connector("kafka", KafkaConnector)

# 3. Use it in config.yaml
# sources:
#   - name: events
#     type: kafka
#     options: { bootstrap_servers: "...", topic: "..." }
```
