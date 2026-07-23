# Backend Testing Guide

## Running Tests Locally

Prerequisites:
- Python 3.12+
- Dependencies installed: `pip install -r requirements.txt`

### Run all tests
```bash
cd backend
python -m pytest tests/ -v
```

### Run tests with coverage
```bash
cd backend
python -m pytest tests/ --cov=app.services --cov-report=html --cov-report=term
```

Coverage report will be generated in `htmlcov/index.html`

### Run specific test file
```bash
cd backend
python -m pytest tests/test_portfolio_service.py -v
```

### Run specific test
```bash
cd backend
python -m pytest tests/test_portfolio_service.py::test_list_portfolios -v
```

## Running Tests in Docker

### Build image with test dependencies
```bash
docker-compose build backend
```

### Run tests in container
```bash
docker-compose exec -T backend python -m pytest tests/ -v
```

### Run tests with coverage in container
```bash
docker-compose exec -T backend python -m pytest tests/ --cov=app.services --cov-report=term
```

## Test Structure

The backend currently has more than 100 tracked test modules, organized under
`tests/`, `tests/services/`, `tests/integrations/`, and `tests/unit/`.

The suite covers authentication, portfolios, transactions, canonical valuation,
snapshots, returns, dividends, market providers, CSV import, administration,
pre-production safety contracts, CLI behavior, migrations, and public API/docs
compliance. Use `pytest --collect-only -q` when an exact current inventory is
required; do not maintain a manual count here.

## Test Coverage

All test files compile successfully and are designed to test:
- Happy path scenarios
- Edge cases and error conditions
- Database interactions with AsyncSession mocking
- External API integrations (mocked)
- Cache operations (Redis)
- Async/await patterns with pytest-asyncio

## Debugging

To see more detailed output:
```bash
python -m pytest tests/ -vv --tb=long
```

To stop on first failure:
```bash
python -m pytest tests/ -x
```

To run tests matching a keyword:
```bash
python -m pytest tests/ -k "portfolio"
```

## Notes

- Tests require `pytest==9.1.0` and `pytest-asyncio==1.4.0` (included in `requirements-test.txt`)
- All external dependencies (API calls, cache operations) are mocked for reliability
- Tests can be run in isolation without a running database or external services
