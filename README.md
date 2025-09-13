# 🚀 Kachi - Enterprise Usage-Based Billing Platform

<div align="center">

![Kachi Logo](https://via.placeholder.com/200x80/3B82F6/FFFFFF?text=KACHI)

**A comprehensive dual-rail usage billing platform that transforms raw telemetry data into accurate, real-time billing**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Vue.js 3](https://img.shields.io/badge/vue.js-3.0+-green.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.100+-teal.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-14+-blue.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[🎯 Features](#-features) • [🏗️ Architecture](#️-architecture) • [🚀 Quick Start](#-quick-start) • [📊 Dashboard](#-dashboard) • [🔧 API Reference](#-api-reference)

</div>

---

## 🎯 Features

### 💡 **Core Capabilities**
- **📡 OpenTelemetry Integration**: Native ingestion of OTEL spans and custom events
- **⚡ Real-time Processing**: Event-driven architecture with millisecond latency
- **🎛️ Flexible Rating Engine**: Complex pricing policies with precedence and envelopes
- **💳 Billing Integration**: Seamless integration with Lago and other billing platforms
- **📊 Advanced Analytics**: ML-powered forecasting and anomaly detection
- **🔒 Enterprise Security**: JWT authentication, RBAC, and audit logging

### 🎨 **Dashboard Features**
- **📈 Real-time Usage Charts**: Interactive visualizations with Chart.js
- **👥 Customer Segmentation**: AI-powered customer behavior analysis
- **🔮 Usage Forecasting**: Predictive analytics with confidence intervals
- **🚨 Anomaly Detection**: Proactive monitoring with configurable alerts
- **💰 Billing Preview**: Cost projections and scenario modeling
- **📋 Export & Reporting**: PDF/CSV exports for compliance and analysis

---

## 🏗️ Architecture

### 🔄 **Data Flow**

```mermaid
graph TD
    A[OpenTelemetry Events] --> B[Ingest API]
    B --> C[Event Queue]
    C --> D[Edge Deriver]
    C --> E[Work Deriver]
    D --> F[Meter Readings]
    E --> F
    F --> G[Rating Engine]
    G --> H[Rated Usage]
    H --> I[Lago Billing]
    H --> J[Analytics Dashboard]

    style A fill:#e1f5fe
    style I fill:#f3e5f5
    style J fill:#e8f5e8
```

### 🏢 **Service Architecture**

| Service | Purpose | Technology | Port |
|---------|---------|------------|------|
| **Ingest API** | Event ingestion & validation | FastAPI + PostgreSQL | 8001 |
| **Deriver** | Event processing & transformation | Python + Celery | - |
| **Rating Engine** | Usage pricing & calculations | Python + SQLAlchemy | - |
| **Dashboard API** | Analytics & admin endpoints | FastAPI + Redis | 8002 |
| **Frontend** | User interface & visualizations | Vue.js 3 + Tailwind | 5173 |
| **Lago Adapter** | Billing system integration | Python + HTTP | - |

### 📦 **Core Components**

#### 1. **📥 Ingest API** (`src/kachi/apps/ingest_api/`)
```python
# Receives OpenTelemetry spans and outcome events
POST /v1/traces          # OTEL span ingestion
POST /v1/outcome-events  # Custom business events
GET  /health            # Service health check
```

#### 2. **⚙️ Event Derivers** (`src/kachi/apps/deriver/`)
- **🌐 Edge Deriver**: API calls, external services, network operations
- **🔧 Work Deriver**: Workflows, internal processes, compute operations
- **📊 Real-time Processing**: Event-driven with automatic retry and DLQ

#### 3. **💰 Rating Engine** (`src/kachi/apps/rater/`)
```python
# Sophisticated pricing with multiple strategies
- Tiered pricing (graduated, volume)
- Usage-based billing (per-unit, per-request)
- Commitment-based pricing (reserved capacity)
- Custom enterprise contracts
```

#### 4. **🔗 Lago Integration** (`src/kachi/apps/lago_adapter/`)
- Customer synchronization
- Plan and pricing management
- Usage event streaming
- Invoice webhook handling

#### 5. **📊 Dashboard & Analytics** (`src/kachi/apps/dashboard_api/`)
- Real-time metrics and KPIs
- Customer usage analytics
- Revenue and forecasting
- System health monitoring

---

## 🚀 Quick Start

### 📋 **Prerequisites**

- **Python 3.12+** with `uv` package manager
- **PostgreSQL 14+** for data persistence
- **Node.js 18+** for frontend development
- **Redis** (optional, for caching and sessions)

### ⚡ **Installation**

1. **Clone and Setup**
```bash
git clone https://github.com/your-org/kachi.git
cd kachi

# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend/dashboard && npm install && cd ../..
```

2. **Database Setup**
```bash
# Create database
createdb kachi

# Run migrations
uv run alembic upgrade head

# Seed sample data (optional)
uv run python scripts/seed_data.py
```

3. **Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Start Services**
```bash
# Start all services with one command
make dev

# Or start services individually
make start-ingest-api    # Port 8001
make start-dashboard-api # Port 8002
make start-frontend      # Port 5173
make start-workers       # Background processing
```

### 🎯 **Verify Installation**

```bash
# Check service health
curl http://localhost:8001/health  # Ingest API
curl http://localhost:8002/health  # Dashboard API

# Access dashboard
open http://localhost:5173
```

---

## 📊 Dashboard

### 🏠 **Main Dashboard**
- **Real-time Metrics**: Live usage, revenue, and system health
- **Customer Overview**: Active customers, growth trends, churn risk
- **Usage Trends**: Interactive charts with drill-down capabilities

### 👥 **Customer Analytics**
- **Segmentation**: Enterprise, Growth, Stable, At-Risk customers
- **Usage Patterns**: Detailed usage analysis per customer
- **Revenue Attribution**: Customer lifetime value and contribution

### 🔮 **Forecasting & Predictions**
- **Usage Forecasting**: ML-powered predictions with confidence bands
- **Revenue Projections**: Financial planning and capacity management
- **Anomaly Detection**: Proactive monitoring with smart alerts

### 💰 **Billing & Revenue**
- **Billing Preview**: Cost projections and scenario modeling
- **Revenue Analytics**: Detailed revenue breakdowns and trends
- **Export Tools**: PDF reports and CSV data exports

---

## 🔧 API Reference

### 📥 **Ingest API** (Port 8001)

#### Send Usage Events
```bash
# OpenTelemetry Spans
curl -X POST http://localhost:8001/v1/traces \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "customer-123",
    "span_id": "span-456",
    "operation_name": "api.call",
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-01-01T00:00:01Z",
    "attributes": {
      "http.method": "GET",
      "http.status_code": 200
    }
  }'

# Outcome Events
curl -X POST http://localhost:8001/v1/outcome-events \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "customer-123",
    "event_type": "workflow.completed",
    "timestamp": "2024-01-01T00:00:00Z",
    "properties": {
      "workflow_id": "wf-789",
      "duration_ms": 1500,
      "success": true
    }
  }'
```

### 📊 **Dashboard API** (Port 8002)

#### Analytics Endpoints
```bash
# Customer Segmentation
curl "http://localhost:8002/api/analytics/segmentation?metric=revenue"

# Usage Forecasting
curl "http://localhost:8002/api/analytics/forecast?period=30&meter_key=api.calls"

# Anomaly Detection
curl "http://localhost:8002/api/analytics/anomalies?time_range=24h&sensitivity=medium"

# Revenue Analytics
curl "http://localhost:8002/api/analytics/revenue?period=30d&breakdown=daily"

# Billing Preview
curl "http://localhost:8002/api/billing/preview?customer_id=123&usage_scenario=current&period_start=2024-01-01&period_end=2024-01-31"
```

#### Customer Management
```bash
# List Customers
curl "http://localhost:8002/api/customers"

# Customer Detailed Usage
curl "http://localhost:8002/api/customers/123/usage/detailed?start_date=2024-01-01&end_date=2024-01-31&granularity=daily"

# Usage Comparison
curl "http://localhost:8002/api/usage/comparison?customer_ids=123,456,789&period=30d&metric=total"
```

#### System Monitoring
```bash
# System Health
curl "http://localhost:8002/api/system/health"

# Alerts
curl "http://localhost:8002/api/alerts?severity=critical&status=active"
```

---

## 🛠️ Development

### 🧪 **Testing**

Kachi includes a comprehensive test suite with multiple testing strategies:

```bash
# Run all tests
make test

# Run specific test categories
make test-unit          # Unit tests
make test-integration   # Integration tests
make test-performance   # Performance benchmarks
make test-property      # Property-based tests

# Run with coverage
make test-coverage

# Run specific test file
uv run pytest tests/test_dashboard_api.py -v
```

### 🔍 **Code Quality**

```bash
# Linting and formatting
make lint               # Run ruff linting
make format             # Format code with ruff
make type-check         # Run mypy type checking

# Pre-commit hooks
make install-hooks      # Install pre-commit hooks
```

### 🐳 **Docker Development**

```bash
# Build and run with Docker Compose
docker-compose up -d

# Run specific services
docker-compose up postgres redis
docker-compose up ingest-api dashboard-api
```

### 📊 **Monitoring & Observability**

- **Health Checks**: All services expose `/health` endpoints
- **Metrics**: Prometheus-compatible metrics at `/metrics`
- **Logging**: Structured JSON logging with correlation IDs
- **Tracing**: OpenTelemetry integration for distributed tracing

---

## 🏢 Production Deployment

### 🚀 **Deployment Options**

#### **Docker Compose** (Recommended for development)
```bash
# Production-ready compose file
docker-compose -f docker-compose.prod.yml up -d
```

#### **Kubernetes** (Recommended for production)
```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/
```

#### **Cloud Platforms**
- **AWS**: ECS, EKS, or Lambda deployment options
- **GCP**: Cloud Run, GKE deployment
- **Azure**: Container Instances, AKS deployment

### 🔧 **Configuration**

#### **Environment Variables**
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/kachi
DATABASE_POOL_SIZE=20

# Redis (optional)
REDIS_URL=redis://host:6379/0

# Lago Integration
LAGO_API_URL=https://api.lago.dev
LAGO_API_KEY=your-lago-api-key
LAGO_WEBHOOK_SECRET=your-webhook-secret

# Security
JWT_SECRET_KEY=your-jwt-secret
API_KEY_SALT=your-api-key-salt

# Monitoring
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO
```

#### **Scaling Considerations**
- **Database**: Use connection pooling and read replicas
- **API Services**: Horizontal scaling with load balancers
- **Background Workers**: Scale Celery workers based on queue depth
- **Frontend**: CDN deployment for static assets

---

## 📚 Documentation

### 📖 **Additional Resources**

- **[API Documentation](docs/api.md)**: Complete API reference
- **[Architecture Guide](docs/architecture.md)**: Detailed system design
- **[Deployment Guide](docs/deployment.md)**: Production deployment
- **[Contributing Guide](CONTRIBUTING.md)**: Development guidelines
- **[Changelog](CHANGELOG.md)**: Version history and updates

### 🎓 **Tutorials**

- **[Getting Started Tutorial](docs/tutorials/getting-started.md)**
- **[Custom Pricing Policies](docs/tutorials/pricing-policies.md)**
- **[Dashboard Customization](docs/tutorials/dashboard-customization.md)**
- **[API Integration Examples](docs/tutorials/api-integration.md)**

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### 🐛 **Bug Reports**
- Use GitHub Issues for bug reports
- Include reproduction steps and environment details
- Add relevant logs and error messages

### 💡 **Feature Requests**
- Discuss new features in GitHub Discussions
- Provide use cases and requirements
- Consider implementation complexity

### 🔧 **Development Process**
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run the test suite (`make test`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **[Lago](https://www.getlago.com/)** for billing platform integration
- **[OpenTelemetry](https://opentelemetry.io/)** for observability standards
- **[FastAPI](https://fastapi.tiangolo.com/)** for the excellent Python framework
- **[Vue.js](https://vuejs.org/)** for the reactive frontend framework

---

<div align="center">

**Built with ❤️ by the Kachi Team**

[🌟 Star us on GitHub](https://github.com/your-org/kachi) • [📧 Contact Us](mailto:team@kachi.dev) • [🐦 Follow Us](https://twitter.com/kachi_dev)

</div>
