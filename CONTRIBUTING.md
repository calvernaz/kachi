# Contributing to Kachi

Thank you for your interest in contributing to Kachi! This guide will help you get started with contributing to our dual-rail usage billing platform.

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+ and Yarn
- PostgreSQL 14+
- Redis
- Git

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/kachi.git
   cd kachi
   ```

2. **Set up the development environment**
   ```bash
   make dev-setup
   ```

3. **Run tests to ensure everything works**
   ```bash
   make test-fast
   ```

## 📋 Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch names:
- `feature/add-usage-forecasting`
- `fix/dashboard-loading-issue`
- `docs/update-api-documentation`

### 2. Make Your Changes

- Write clean, readable code
- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run all tests
make test

# Run specific test categories
make test-unit
make test-integration

# Check code quality
make quality-check
```

### 4. Commit Your Changes

We use conventional commits for clear commit messages:

```bash
git commit -m "feat: add usage forecasting endpoint"
git commit -m "fix: resolve dashboard loading issue"
git commit -m "docs: update API documentation"
```

**Commit Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub with:
- Clear title and description
- Reference any related issues
- Include screenshots for UI changes
- Ensure all checks pass

## 🧪 Testing Guidelines

### Test Categories

1. **Unit Tests** (`tests/test_*.py`)
   - Test individual functions and classes
   - Mock external dependencies
   - Fast execution

2. **Integration Tests** (`tests/test_integration.py`)
   - Test complete workflows
   - Use real database connections
   - Test API endpoints end-to-end

3. **Property-Based Tests** (`tests/test_property_based.py`)
   - Use Hypothesis for generative testing
   - Test edge cases and invariants

4. **Performance Tests** (`tests/test_performance.py`)
   - Verify system performance
   - Test under load conditions

### Writing Tests

```python
# Example unit test
def test_usage_calculation():
    """Test usage calculation logic."""
    policy = UsageBasedPolicy(base_rate=Decimal('0.10'))
    cost = policy.calculate_cost(100)
    assert cost == Decimal('10.00')

# Example integration test
@pytest.mark.asyncio
async def test_customer_creation_workflow(db_session):
    """Test complete customer creation workflow."""
    # Create customer
    customer = Customer(name="Test Customer")
    db_session.add(customer)
    await db_session.commit()

    # Verify customer was created
    assert customer.id is not None
```

### Test Fixtures

Use pytest fixtures for common test data:

```python
@pytest.fixture
async def sample_customer(db_session):
    """Create a sample customer for testing."""
    customer = Customer(name="Test Customer")
    db_session.add(customer)
    await db_session.commit()
    return customer
```

## 🎨 Code Style

### Python

We use Ruff for linting and formatting:

```bash
# Check code style
make lint

# Format code
make format

# Type checking
make type-check
```

**Key Guidelines:**
- Use type hints for all function parameters and return values
- Follow PEP 8 naming conventions
- Use descriptive variable and function names
- Add docstrings for public functions and classes
- Keep functions small and focused

### TypeScript/Vue.js

```bash
cd frontend/dashboard

# Lint frontend code
yarn lint

# Type check
yarn type-check
```

**Key Guidelines:**
- Use TypeScript for type safety
- Follow Vue.js 3 Composition API patterns
- Use Pinia for state management
- Follow component naming conventions

## 📚 Documentation

### Code Documentation

- Add docstrings to all public functions and classes
- Use type hints consistently
- Include examples in docstrings when helpful

```python
def calculate_usage_cost(
    usage: float,
    policy: PricingPolicy,
    customer_id: UUID
) -> Decimal:
    """Calculate the cost for a given usage amount.

    Args:
        usage: The usage amount to calculate cost for
        policy: The pricing policy to apply
        customer_id: The customer ID for context

    Returns:
        The calculated cost as a Decimal

    Example:
        >>> policy = UsageBasedPolicy(base_rate=Decimal('0.10'))
        >>> cost = calculate_usage_cost(100.0, policy, customer_id)
        >>> print(cost)
        10.00
    """
```

### API Documentation

- Update OpenAPI schemas when adding new endpoints
- Include request/response examples
- Document error responses

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Clear description** of the issue
2. **Steps to reproduce** the problem
3. **Expected behavior** vs actual behavior
4. **Environment details** (OS, Python version, etc.)
5. **Error messages** and stack traces
6. **Screenshots** for UI issues

Use our bug report template:

```markdown
## Bug Description
Brief description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: macOS 14.0
- Python: 3.12.0
- Browser: Chrome 120.0

## Additional Context
Any other relevant information
```

## 💡 Feature Requests

For feature requests, please:

1. **Check existing issues** to avoid duplicates
2. **Describe the problem** you're trying to solve
3. **Propose a solution** with implementation details
4. **Consider alternatives** and trade-offs
5. **Provide use cases** and examples

## 🔍 Code Review Process

### For Contributors

- Ensure all tests pass
- Keep pull requests focused and small
- Respond to feedback promptly
- Update your branch with latest main if needed

### For Reviewers

- Be constructive and helpful
- Focus on code quality and maintainability
- Check for test coverage
- Verify documentation updates
- Test the changes locally when possible

## 📞 Getting Help

- **GitHub Discussions**: For questions and general discussion
- **GitHub Issues**: For bug reports and feature requests
- **Documentation**: Check our docs at docs.kachi.dev

## 🙏 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes for significant contributions
- GitHub contributor graphs

Thank you for contributing to Kachi! 🎉
