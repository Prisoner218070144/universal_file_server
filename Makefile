.PHONY: test test-unit test-integration test-functional coverage clean

test: test-unit test-integration test-functional

test-unit:
	pytest tests/unit/ -v --tb=short

test-integration:
	pytest tests/integration/ -v --tb=short

test-functional:
	pytest tests/functional/ -v --tb=short

coverage:
	pytest --cov=models --cov=utils --cov=controllers --cov=app --cov-report=html --cov-report=term-missing tests/

coverage-xml:
	pytest --cov=models --cov=utils --cov=controllers --cov=app --cov-report=xml tests/

lint:
	flake8 app.py config.py controllers/ models/ utils/ views/

format:
	black app.py config.py controllers/ models/ utils/ views/ tests/
	isort app.py config.py controllers/ models/ utils/ views/ tests/

clean:
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	rm -rf */__pycache__/
	rm -rf */*/__pycache__/
	find . -name "*.pyc" -delete

all: format lint test coverage