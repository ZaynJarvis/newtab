# Monitoring Setup Guide

This guide explains how to set up and use the observability stack for the New Tab application.

## Quick Start

### Option 1: Use Setup Script (Recommended)
```bash
# Setup and start monitoring stack
./scripts/setup-monitoring.sh

# Start main application
docker-compose up -d
```

### Option 2: Manual Setup
```bash
# Create shared network
docker network create newtab-monitoring

# Start monitoring stack
docker-compose -f docker-compose.observe.yml up -d

# Start main application
docker-compose up -d
```

### 3. Access Dashboards
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **cAdvisor**: http://localhost:8080

## Network Architecture

The monitoring setup uses a **shared Docker network** (`newtab-monitoring`) to enable communication between the main application and monitoring services:

```
┌─────────────────┐    ┌─────────────────┐
│  Main App       │    │  Monitoring     │
│  (docker-       │    │  (docker-       │
│   compose.yml)  │    │   compose.      │
│                 │    │   observe.yml)  │
│ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │newtab-      │ │    │ │prometheus   │ │
│ │backend      │◄┼────┼►│grafana      │ │
│ │             │ │    │ │cadvisor     │ │
│ └─────────────┘ │    │ │loki         │ │
└─────────────────┘    │ └─────────────┘ │
                       └─────────────────┘
         │                       │
         └───────────────────────┘
           newtab-monitoring network
```

This architecture allows:
- **Prometheus** to scrape metrics from `newtab-backend:8000`
- **Promtail** to collect logs from backend container
- **cAdvisor** to monitor all containers including the backend
- **Independent operation** - either stack can run without the other

## Architecture Overview

The monitoring stack consists of:

### Core Components
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **cAdvisor**: Container metrics collection
- **Node Exporter**: System-level metrics

### Optional Components
- **Loki**: Log aggregation
- **Promtail**: Log collection agent

## Service Details

### Prometheus (Port 9090)
Collects metrics from:
- cAdvisor (container metrics)
- Node Exporter (system metrics)
- Application metrics (if enabled)

**Configuration**: `config/prometheus/prometheus.yml`

### Grafana (Port 3000)
Pre-configured with:
- Prometheus datasource
- Loki datasource (for logs)
- Auto-provisioned dashboards

**Default Login**: admin/admin123 (change via GRAFANA_ADMIN_PASSWORD)

### cAdvisor (Port 8080)
Provides detailed container metrics:
- CPU usage
- Memory consumption
- Network I/O
- Disk I/O
- Container lifecycle events

### Loki (Port 3100)
Log aggregation service that collects:
- Application logs from `/logs` directory
- Docker container logs (via Promtail)

## Configuration

### Environment Variables
Key monitoring settings in `.env`:
```bash
GRAFANA_ADMIN_PASSWORD=admin123
PROMETHEUS_RETENTION=15d
LOKI_RETENTION_PERIOD=168h
```

### Log Collection
Promtail automatically collects:
- New Tab backend logs from `/logs/backend/`
- Docker container logs (stdout/stderr)

### Service Discovery
Prometheus automatically discovers:
- Container metrics via cAdvisor
- System metrics via Node Exporter
- Application metrics (if exposed)

## Usage

### Viewing Container Metrics
1. Open Grafana at http://localhost:3000
2. Login with admin/admin123
3. Navigate to Docker dashboards
4. View real-time container metrics

### Exploring Logs
1. In Grafana, go to "Explore"
2. Select "Loki" datasource
3. Query logs with LogQL:
   ```
   {service="backend"} |= "ERROR"
   ```

### Setting Up Alerts
1. In Grafana, go to "Alerting"
2. Create alert rules based on metrics
3. Configure notification channels

## Maintenance

### Starting/Stopping Services
```bash
# Start monitoring stack
docker-compose -f docker-compose.observe.yml up -d

# Stop monitoring stack
docker-compose -f docker-compose.observe.yml down

# View logs
docker-compose -f docker-compose.observe.yml logs -f
```

### Data Management
- **Prometheus data**: Retained for 15 days (configurable)
- **Grafana dashboards**: Persisted in Docker volume
- **Loki logs**: Retained for 7 days (168h)

### Backup
```bash
# Backup Grafana data
docker run --rm -v newtab-grafana-data:/source -v $(pwd):/backup alpine tar czf /backup/grafana-backup.tar.gz -C /source .

# Backup Prometheus data
docker run --rm -v newtab-prometheus-data:/source -v $(pwd):/backup alpine tar czf /backup/prometheus-backup.tar.gz -C /source .
```

## Troubleshooting

### Common Issues

**Grafana login fails**
- Check GRAFANA_ADMIN_PASSWORD in .env
- Reset password: `docker-compose -f docker-compose.observe.yml exec grafana grafana-cli admin reset-admin-password newpassword`

**No metrics in Prometheus**
- Check if cAdvisor is running: `docker-compose -f docker-compose.observe.yml ps`
- Verify targets in Prometheus UI: http://localhost:9090/targets
- Ensure network exists: `docker network ls | grep newtab-monitoring`
- Check backend is on monitoring network: `docker inspect newtab-backend | grep newtab-monitoring`

**Backend metrics not accessible**
- Verify network connectivity: `docker exec newtab-prometheus ping newtab-backend`
- Check if backend exposes metrics endpoint: `curl http://localhost:8000/metrics`
- Ensure both services are on the monitoring network

**Missing logs in Loki**
- Check Promtail configuration: `config/promtail/config.yml`
- Verify log directory permissions: `ls -la logs/`
- Check Docker socket access: `docker exec newtab-promtail ls -la /var/run/docker.sock`

**Network connection issues**
```bash
# Check if monitoring network exists
docker network ls | grep newtab-monitoring

# Create network if missing
docker network create newtab-monitoring

# Check which containers are connected
docker network inspect newtab-monitoring

# Reconnect backend to monitoring network
docker network connect newtab-monitoring newtab-backend
```

### Resource Usage
Monitor resource consumption:
```bash
# Check container resource usage
docker stats

# Check disk usage
df -h
du -sh logs/
```

## Security Notes

### Production Considerations
1. **Change default passwords**: Update GRAFANA_ADMIN_PASSWORD
2. **Network security**: Use reverse proxy for external access
3. **Access control**: Configure Grafana authentication
4. **Data retention**: Adjust retention periods based on requirements

### Firewall Configuration
If exposing externally, secure these ports:
- 3000 (Grafana) - Use HTTPS and authentication
- 9090 (Prometheus) - Internal access only
- 8080 (cAdvisor) - Internal access only

## Advanced Configuration

### Custom Dashboards
1. Create dashboard JSON files in `config/grafana/dashboards/`
2. Restart Grafana to auto-import
3. Or import via Grafana UI

### Alert Rules
Create `config/prometheus/rules/alerts.yml`:
```yaml
groups:
- name: container.rules
  rules:
  - alert: ContainerHighMemory
    expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.8
    for: 5m
    annotations:
      summary: "Container memory usage is above 80%"
```

### External Exporters
Add custom metrics exporters to `docker-compose.observe.yml`:
```yaml
  custom-exporter:
    image: your/exporter:latest
    ports:
      - "9999:9999"
    networks:
      - monitoring
```

Then update Prometheus configuration to scrape the new exporter.

## Performance Tuning

### Prometheus Optimization
- Adjust `scrape_interval` based on requirements
- Configure `storage.tsdb.retention.time` for data retention
- Use recording rules for expensive queries

### Grafana Optimization
- Enable caching for dashboards
- Limit query time ranges
- Use template variables for dynamic dashboards

### Resource Limits
Set resource limits in docker-compose.observe.yml:
```yaml
  prometheus:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```