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

21 comprehensive test files covering all major services:
- Authentication & User Management: `test_auth_service.py`, `test_user_service.py`
- Portfolio Management: `test_portfolio_service.py`, `test_transaction_service.py`, `test_position_service.py`
- Financial Data: `test_proventos_service.py`, `test_dividend_service.py`, `test_dividends_sync_service.py`, `test_dividend_backfill_service.py`
- Quotes & Assets: `test_quotes_service.py`, `test_asset_service.py`, `test_class_target_service.py`
- Analysis & Reports: `test_performance_service.py`, `test_irpf_service.py`, `test_rentabilidade_service.py`, `test_treasury_service.py`
- Administration: `test_audit_log_service.py`, `test_backup_service.py`, `test_csv_import_service.py`
- Configuration: `test_config_service.py`, `test_goals_service.py`

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

- Tests require `pytest==9.1.0` and `pytest-asyncio==1.4.0` (included in `requirements.txt`)
- All external dependencies (API calls, cache operations) are mocked for reliability
- Tests can be run in isolation without a running database or external services
