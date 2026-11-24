-- Keyspace para series temporais de sensores industriais (SimpleStrategy para ambiente local)
CREATE KEYSPACE IF NOT EXISTS iot_timeseries
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

-- Tabela orientada a consulta: leituras recentes de um sensor dentro de um dia (evita unbounded partitions)
CREATE TABLE IF NOT EXISTS iot_timeseries.sensor_readings_by_day (
    sensor_id text,
    bucket_date date,
    event_ts timestamp,
    machine_id text,
    line_id text,
    sensor_type text,
    value double,
    unit text,
    status text,
    batch_id text,
    PRIMARY KEY ((sensor_id, bucket_date), event_ts)
) WITH CLUSTERING ORDER BY (event_ts DESC)
  AND default_time_to_live = 2592000;
