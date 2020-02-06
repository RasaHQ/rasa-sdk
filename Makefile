.PHONY: clean test lint init check-readme

TEST_PATH=./

help:
	@echo "    clean"
	@echo "        Remove python artifacts and build artifacts."
	@echo "    lint"
	@echo "        Check style with flake8."
	@echo "    test"
	@echo "        Run py.test"
	@echo "    init"
	@echo "        Install Rasa SDK dependencies"
	@echo "    release"
	@echo "        Prepare a new release"

init:
	poetry install

clean:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f  {} +
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf docs/_build

types:
	pytype --keep-going rasa_sdk

lint:
	flake8 rasa_sdk tests
	black --check rasa_sdk tests

test: clean
	py.test tests --cov rasa_sdk -W ignore

release:
	python3 scripts/release.py
