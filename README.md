# Kachi - Dual-Rail Usage Billing Platform

[![Tests](https://github.com/calvernaz/kachi/actions/workflows/tests.yml/badge.svg)](https://github.com/calvernaz/kachi/actions/workflows/tests.yml)
[![Coverage](https://codecov.io/gh/calvernaz/kachi/branch/main/graph/badge.svg)](https://codecov.io/gh/calvernaz/kachi)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Kachi is a modern, high-performance dual-rail usage billing platform designed for SaaS companies that need sophisticated usage tracking, rating, and billing capabilities. Built with Python, FastAPI, and Vue.js, it provides real-time usage monitoring, flexible pricing models, and seamless integration with billing systems like Lago.

## 🚀 Features

### Core Billing Engine
- **Dual-Rail Architecture**: Separate tracking for edges (API calls, requests) and work (processing time, compute)
- **Real-time Usage Tracking**: OpenTelemetry-based ingestion for immediate usage visibility
- **Flexible Rating Engine**: Support for tiered pricing, volume discounts, and custom pricing policies
- **Lago Integration**: Seamless integration with Lago billing platform for invoicing and payments

### Dashboard & Analytics
- **Modern Vue.js Dashboard**: Real-time usage visualization and customer management
- **Usage Forecasting**: Predictive analytics for usage patterns and cost estimation
- **Drill-down Analytics**: Detailed usage breakdowns by customer, meter, and time period
- **Alert System**: Configurable alerts for usage thresholds and anomalies

### Developer Experience
- **OpenTelemetry Integration**: Standard observability for usage tracking
- **RESTful APIs**: Comprehensive APIs for all platform functionality
- **Type Safety**: Full TypeScript support in frontend and Python type hints in backend
- **Comprehensive Testing**: Unit, integration, property-based, and performance tests

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Vue.js 3      │    │   FastAPI       │    │   PostgreSQL    │
│   Dashboard     │◄──►│   APIs          │◄──►│   Database      │
│   (Frontend)    │    │   (Backend)     │    │   (Storage)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Lago Billing  │
                    │   Integration   │
                    └─────────────────┘
```

### Components

- **Ingestion API**: Receives OpenTelemetry data and outcome events
- **Event Processors**: Transform raw events into meter readings
- **Rating Engine**: Applies pricing policies to calculate costs
- **Dashboard API**: Provides data for the frontend dashboard
- **Lago Adapter**: Syncs usage data with Lago billing platform

## 🛠️ Technology Stack

### Backend
- **Python 3.12+** with modern async/await patterns
- **FastAPI** for high-performance APIs
- **SQLAlchemy 2.0** with async support
- **PostgreSQL** for reliable data storage
- **Alembic** for database migrations
- **Celery** for background task processing

### Frontend
- **Vue.js 3** with Composition API
- **TypeScript** for type safety
- **Vite** for fast development and building
- **Tailwind CSS 3** for modern styling
- **Pinia** for state management

### Development & Testing
- **uv** for fast Python package management
- **pytest** with async support
- **Hypothesis** for property-based testing
- **Ruff** for linting and formatting
- **MyPy** for static type checking

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **Node.js 18+** and **Yarn**
- **PostgreSQL 14+**
- **Redis** (for Celery task queue)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/calvernaz/kachi.git
   cd kachi
   ```

2. **Set up Python environment**
   ```bash
   # Install uv if you haven't already
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install dependencies
   make install
   ```

3. **Set up the database**
   ```bash
   # Create PostgreSQL database
   createdb kachi_dev

   # Run migrations
   make db-migrate
   ```

4. **Set up frontend**
   ```bash
   cd frontend/dashboard
   yarn install
   cd ../..
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database and API keys
   ```

### Running the Application

1. **Start the backend services**
   ```bash
   # Terminal 1: Ingestion API
   make run-ingest

   # Terminal 2: Dashboard API
   make run-dashboard
   ```

2. **Start the frontend**
   ```bash
   # Terminal 3: Frontend development server
   make run-frontend
   ```

3. **Access the application**
   - Dashboard: http://localhost:5174
   - Ingestion API: http://localhost:8001
   - Dashboard API: http://localhost:8002
   - API Documentation: http://localhost:8001/docs

## 📊 Usage Examples

### Sending Usage Data

```python
import requests
from datetime import datetime

# Send OpenTelemetry span data
otel_data = {
    "resource_spans": [{
        "resource": {"attributes": {}},
        "scope_spans": [{
            "spans": [{
                "trace_id": "12345678901234567890123456789012",
                "span_id": "1234567890123456",
                "name": "api_call",
                "start_time_unix_nano": int(datetime.now().timestamp() * 1e9),
                "attributes": {
                    "billing.customer_id": "customer_123",
                    "http.method": "GET",
                    "http.route": "/api/v1/users"
                }
            }]
        }]
    }]
}

response = requests.post(
    "http://localhost:8001/v1/otel",
    json=otel_data
)
```

### Retrieving Usage Data

```python
import requests

# Get customer usage summary
response = requests.get(
    "http://localhost:8002/v1/customers/customer_123/usage/summary"
)

usage_data = response.json()
print(f"Customer: {usage_data['customer_id']}")
for meter in usage_data['meters']:
    print(f"  {meter['name']}: {meter['current_usage']}/{meter['limit']}")

## 🧪 Testing

Kachi includes comprehensive testing infrastructure:

```bash
# Run all tests
make test

# Run specific test categories
make test-unit          # Unit tests only
make test-integration   # Integration tests
make test-performance   # Performance tests
make test-property      # Property-based tests

# Run tests with coverage
make test-coverage

# Run fast tests (skip slow ones)
make test-fast
```

### Test Categories

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test complete workflows end-to-end
- **Property-Based Tests**: Use Hypothesis for generative testing
- **Performance Tests**: Verify system performance under load

## 🔧 Development

### Code Quality

```bash
# Run all quality checks
make quality-check

# Individual checks
make lint           # Ruff linting
make format         # Code formatting
make type-check     # MyPy type checking
```

### Database Operations

```bash
# Create new migration
uv run alembic revision --autogenerate -m "Description"

# Apply migrations
make db-migrate

# Reset database
make db-reset
```

### Adding New Features

1. **Create feature branch**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Implement changes with tests**
   ```bash
   # Add your code
   # Write comprehensive tests
   make test
   ```

3. **Ensure code quality**
   ```bash
   make quality-check
   ```

4. **Submit pull request**

## 🚀 Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
make docker-build
make docker-run
```

### Production Deployment

1. **Set environment variables**
   ```bash
   export DATABASE_URL="postgresql://..."
   export LAGO_API_KEY="..."
   export REDIS_URL="redis://..."
   ```

2. **Deploy to your platform**
   ```bash
   # Example for staging
   make deploy-staging

   # Example for production
   make deploy-production
   ```

## 📚 API Documentation

- **Ingestion API**: http://localhost:8001/docs
- **Dashboard API**: http://localhost:8002/docs

### Key Endpoints

#### Ingestion API
- `POST /v1/otel` - Submit OpenTelemetry data
- `POST /v1/events/outcome` - Submit outcome events
- `GET /v1/usage/preview` - Preview usage calculations

#### Dashboard API
- `GET /v1/customers` - List customers
- `GET /v1/customers/{id}/usage/summary` - Customer usage summary
- `GET /v1/customers/{id}/meters/{meter}` - Detailed meter data

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all checks pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs.kachi.dev](https://docs.kachi.dev)
- **Issues**: [GitHub Issues](https://github.com/calvernaz/kachi/issues)
- **Discussions**: [GitHub Discussions](https://github.com/calvernaz/kachi/discussions)

## 🙏 Acknowledgments

- [Lago](https://getlago.com) for billing platform integration
- [OpenTelemetry](https://opentelemetry.io) for observability standards
- [FastAPI](https://fastapi.tiangolo.com) for the excellent web framework
- [Vue.js](https://vuejs.org) for the reactive frontend framework
```
