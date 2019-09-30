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

init:
	pip install -r requirements.txt

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
	py.test tests --cov rasa_sdk

check-readme:
	# if this runs through we can be sure the readme is properly shown on pypi
	python setup.py check --restructuredtext --strict
