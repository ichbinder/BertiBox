# Makefile for BertiBox testing

.PHONY: help test test-unit test-integration test-coverage test-verbose clean install-test-deps

help:
	@echo "Available commands:"
	@echo "  make test              - Run all tests"
	@echo "  make test-unit         - Run unit tests only"
	@echo "  make test-integration  - Run integration tests only"
	@echo "  make test-coverage     - Run tests with coverage report"
	@echo "  make test-verbose      - Run tests with verbose output"
	@echo "  make test-failed       - Re-run only failed tests"
	@echo "  make test-specific     - Run specific test file (use TEST=path/to/test.py)"
	@echo "  make clean             - Clean test artifacts"
	@echo "  make install-test-deps - Install test dependencies"

# Install test dependencies
install-test-deps:
	pip install -r test_requirements.txt

# Run all tests
test:
	venv/bin/python -m pytest tests/

# Run unit tests only
test-unit:
	python -m pytest tests/ -m unit

# Run integration tests only  
test-integration:
	python -m pytest tests/ -m integration

# Run tests with coverage report
test-coverage:
	python -m pytest tests/ --cov=. --cov-report=term-missing --cov-report=html

# Run tests with verbose output
test-verbose:
	python -m pytest tests/ -vv

# Re-run only failed tests
test-failed:
	python -m pytest tests/ --lf

# Run specific test file
test-specific:
	python -m pytest $(TEST)

# Run tests for specific module
test-core:
	python -m pytest tests/test_core_player.py -v

test-database:
	python -m pytest tests/test_database_*.py -v

test-api:
	python -m pytest tests/test_api_*.py -v

test-websocket:
	python -m pytest tests/test_websocket_*.py -v

test-utils:
	python -m pytest tests/test_utils_*.py -v

# Clean test artifacts
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf tests/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete