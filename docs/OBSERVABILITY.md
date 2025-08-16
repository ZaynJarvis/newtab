# Observability Improvement Plan

## Executive Summary

This document outlines improvements to logging, monitoring, and observability for the New Tab application. The analysis revealed that logging is functional but needs optimization, and monitoring infrastructure is missing.

## Current State Analysis

### 1. Logging Investigation ✅
**Status**: Logging is working correctly
- Docker logs show structured JSON output from backend application
- Application uses sophisticated logging system (`src/core/logging.py`) with StructuredFormatter
- Logs include request tracking, API calls, and contextual information
- **Issue**: Logs only output to stdout/stderr, no file persistence to host filesystem

### 2. Environment Configuration ✅ 
**Status**: Properly configured
- `.env` file works for both Docker Compose and direct application runs
- Docker Compose properly inherits environment variables
- Configuration includes comprehensive settings for development and production

### 3. Log Management Issues ⚠️
**Current Problems**:
- No log rotation configured - risk of disk exhaustion
- Logs not persisted to host filesystem for analysis
- No automated cleanup of old logs
- Using default `json-file` driver without size limits

### 4. Monitoring Stack Missing ❌
**Current State**: No monitoring infrastructure
- No CPU/memory usage visualization
- No alerting for resource exhaustion
- No centralized metrics collection
- No performance dashboards

## Proposed Solution Architecture

### Phase 1: Log Management Improvements

#### 1.1 Add Log Rotation
```yaml
# In docker-compose.yml
logging:
  driver: "local"  # Better performance than json-file
  options:
    max-size: "10m"
    max-file: "3"
```

#### 1.2 Enable File Logging
- Configure application to write logs to `/app/logs/` (already mounted)
- Ensure structured logs are written to both stdout and files
- Add log file rotation within the application

### Phase 2: Monitoring Stack (Separate docker-compose.observe.yml)

#### 2.1 Core Components
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **cAdvisor**: Container metrics collection
- **Loki** (Optional): Log aggregation

#### 2.2 Architecture Benefits
- **Separation of Concerns**: Main app and monitoring run independently
- **Optional Deployment**: Can enable/disable monitoring without affecting main app
- **Resource Isolation**: Monitoring resources don't impact application performance
- **Independent Scaling**: Monitor multiple environments from single observability stack

## Implementation Plan

### Step 1: Log Rotation Setup
1. Update `docker-compose.yml` with logging configuration
2. Test log rotation with size limits
3. Verify logs are properly rotated and cleaned up

### Step 2: Monitoring Stack Creation
1. Create `docker-compose.observe.yml` with Prometheus/Grafana/cAdvisor
2. Configure Prometheus to scrape Docker metrics
3. Set up Grafana dashboards for container monitoring
4. Configure service discovery for automatic container detection

### Step 3: Integration & Configuration
1. Update `.env` with monitoring-specific settings
2. Create monitoring documentation
3. Set up health checks for monitoring services
4. Configure alerting rules for critical metrics

### Step 4: Documentation & Maintenance
1. Document how to start/stop monitoring stack
2. Create runbooks for common monitoring scenarios
3. Set up automated log cleanup scripts
4. Document dashboard usage and alerting setup

## Expected Benefits

### Immediate Improvements
- **Prevent Disk Exhaustion**: Log rotation prevents unlimited log growth
- **Better Debugging**: Persistent log files enable better troubleshooting
- **Resource Visibility**: Real-time CPU/memory monitoring

### Long-term Benefits
- **Proactive Monitoring**: Alerts before issues become critical
- **Performance Optimization**: Historical metrics help identify bottlenecks
- **Operational Excellence**: Standardized observability practices
- **Scalability**: Foundation for monitoring multiple services

## Technical Specifications

### Log Rotation Configuration
```yaml
# Recommended settings
logging:
  driver: "local"
  options:
    max-size: "10m"    # Maximum size per log file
    max-file: "3"      # Number of rotated files to keep
```

### Monitoring Stack Resource Requirements
- **Prometheus**: 1 CPU core, 2GB RAM minimum
- **Grafana**: 0.5 CPU core, 1GB RAM minimum
- **cAdvisor**: 0.2 CPU core, 500MB RAM minimum
- **Total**: ~2 CPU cores, 4GB RAM for monitoring stack

### Network Configuration
- **Prometheus**: Port 9090 (metrics UI)
- **Grafana**: Port 3000 (dashboards)
- **cAdvisor**: Port 8080 (container metrics)

## Security Considerations

### Access Control
- Grafana admin credentials in environment variables
- Prometheus metrics endpoint protection
- Network isolation between monitoring and application

### Data Retention
- Prometheus metrics retention: 15 days default
- Log file retention: 3 rotated files per service
- Dashboard authentication required

## Maintenance Procedures

### Daily Operations
- Monitor disk usage for log directories
- Check monitoring service health
- Review critical alerts

### Weekly Tasks
- Review dashboard metrics for trends
- Clean up old monitoring data
- Update monitoring configurations as needed

### Monthly Reviews
- Analyze resource usage patterns
- Optimize monitoring queries and dashboards
- Review and update alerting rules

## Next Steps

1. **Immediate**: Implement log rotation to prevent disk issues
2. **Short-term**: Set up basic monitoring stack
3. **Medium-term**: Configure alerting and advanced dashboards
4. **Long-term**: Expand monitoring to additional metrics and services

## Success Metrics

- **Log Management**: No disk space issues due to logs
- **Monitoring Coverage**: 100% visibility into container resources
- **Alert Response**: Critical issues detected within 1 minute
- **Operational Efficiency**: Reduced time to diagnose issues by 50%