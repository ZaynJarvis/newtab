#!/bin/bash
# Setup script for New Tab monitoring stack
# This script ensures proper network configuration and starts the monitoring stack

set -e

echo "🔧 Setting up New Tab monitoring stack..."

# Create the shared monitoring network if it doesn't exist
if ! docker network ls | grep -q "newtab-monitoring"; then
    echo "📡 Creating shared monitoring network..."
    docker network create newtab-monitoring
else
    echo "✅ Monitoring network already exists"
fi

# Start the monitoring stack
echo "🚀 Starting monitoring services..."
docker-compose -f docker-compose.observe.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."

# Check Prometheus
if curl -s http://localhost:9090/-/healthy > /dev/null; then
    echo "✅ Prometheus is healthy"
else
    echo "⚠️  Prometheus might still be starting..."
fi

# Check Grafana
if curl -s http://localhost:3000/api/health > /dev/null; then
    echo "✅ Grafana is healthy"
else
    echo "⚠️  Grafana might still be starting..."
fi

# Check cAdvisor
if curl -s http://localhost:8080/healthz > /dev/null; then
    echo "✅ cAdvisor is healthy"
else
    echo "⚠️  cAdvisor might still be starting..."
fi

echo ""
echo "🎉 Monitoring stack setup complete!"
echo ""
echo "📊 Access your dashboards:"
echo "   • Grafana:    http://localhost:3000 (admin/admin123)"
echo "   • Prometheus: http://localhost:9090"
echo "   • cAdvisor:   http://localhost:8080"
echo ""
echo "📝 Next steps:"
echo "   1. Start your main application: docker-compose up -d"
echo "   2. Check Prometheus targets: http://localhost:9090/targets"
echo "   3. Import dashboards in Grafana"
echo ""
echo "🔍 To monitor your backend, ensure it's running and connected to the newtab-monitoring network"