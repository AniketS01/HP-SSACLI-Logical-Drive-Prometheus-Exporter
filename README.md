# HP SSACLI Logical Drive Prometheus Exporter

A lightweight Prometheus exporter that monitors HP Smart Array logical drive health using `ssacli`.

## Metrics Exposed

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `hp_ssacli_logical_drive_status` | Gauge | `controller`, `logicaldrive`, `size`, `raid_level` | Per-drive status (1=healthy, 0=unhealthy) |
| `hp_ssacli_logical_drives_healthy_total` | Gauge | — | Total healthy drives |
| `hp_ssacli_logical_drives_failed_total` | Gauge | — | Total failed/degraded drives |
| `hp_ssacli_scrape_errors_total` | Counter | — | Scrape error count |

## Quick Start

```bash
pip install -r requirements.txt
python main.py --port 9100
```

The exporter runs on port **9100** by default. Metrics are available at `http://<host>:9100/metrics`.

### Options

```
--port          Port to listen on (default: 9100)
--ssacli-bin    Path to ssacli binary (default: ssacli)
--log-level     DEBUG, INFO, WARNING, ERROR (default: INFO)
```

## Prometheus Scrape Config

```yaml
scrape_configs:
  - job_name: "hp_ssacli"
    static_configs:
      - targets: ["<server-ip>:9100"]
    scrape_interval: 60s
```

## Grafana Alert Rule (example)

Fire an alert when any logical drive is not healthy:

```yaml
groups:
  - name: hp_drive_alerts
    rules:
      - alert: HPLogicalDriveFailed
        expr: hp_ssacli_logical_drives_failed_total > 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "HP logical drive failure detected"
          description: "{{ $value }} logical drive(s) are in a failed/degraded state."
```

## Running Tests

```bash
pip install pytest
pytest test_ssacli.py -v
```
