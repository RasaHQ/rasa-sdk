.PHONY: clean test lint init check-readme docs

TEST_PATH=./

help:
	@echo "    clean"
	@echo "        Remove python artifacts and build artifacts."
	@echo "    lint"
	@echo "        Check style with flake8."
	@echo "    lint-docstrings"
	@echo "        Check docstring conventions in changed files."
	@echo "    test"
	@echo "        Run py.test"
	@echo "    init"
	@echo "        Install Rasa SDK dependencies"
	@echo "    release"
	@echo "        Prepare a new release"

install:
	poetry run python -m pip install -U pip
	poetry install

install-docs:
	cd docs/ && yarn install

clean:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f  {} +
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf docs/build
	rm -rf docs/.docusaurus

types:
	poetry run mypy rasa_sdk

formatter:
	poetry run black rasa_sdk tests

lint:
	poetry run flake8 rasa_sdk tests --extend-ignore D
	poetry run black --check rasa_sdk tests
	make lint-docstrings

 # Compare against `main` if no branch was provided
BRANCH ?= main
lint-docstrings:
# Lint docstrings only against the the diff to avoid too many errors.
# Check only production code. Ignore other flake errors which are captured by `lint`
# Diff of committed changes (shows only changes introduced by your branch)
ifneq ($(strip $(BRANCH)),)
	git diff $(BRANCH)...HEAD -- rasa_sdk | poetry run flake8 --select D --diff
endif
	# Diff of uncommitted changes for running locally
	git diff HEAD -- rasa_sdk | poetry run flake8 --select D --diff

test: clean
	poetry run py.test tests --cov rasa_sdk -v

prepare-docs:
	cd docs/ && poetry run yarn pre-build

docs: prepare-docs
	cd docs/ && yarn build

test-docs: generate-pending-changelog docs

livedocs:
	cd docs/ && poetry run yarn start

preview-docs:
	cd docs/ && yarn build && yarn deploy-preview --alias=${PULL_REQUEST_NUMBER} --message="Preview for Pull Request #${PULL_REQUEST_NUMBER}"

publish-docs:
	cd docs/ && yarn build && yarn deploy

release:
	poetry run python scripts/release.py

