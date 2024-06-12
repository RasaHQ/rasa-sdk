.PHONY: clean test lint init check-readme docs

TEST_PATH=./

help:
	@echo "    clean"
	@echo "        Remove python artifacts and build artifacts."
	@echo "    lint"
	@echo "        Lint with ruff."
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

clean:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f  {} +
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info

types:
	poetry run mypy rasa_sdk

formatter:
	poetry run black rasa_sdk tests

lint:
	poetry run ruff check rasa_sdk tests --ignore D
	poetry run black --check rasa_sdk tests
	make lint-docstrings

 # Compare against `main` if no branch was provided
BRANCH ?= main
lint-docstrings:
	./scripts/lint_python_docstrings.sh $(BRANCH)

test: clean
	poetry run py.test tests --cov rasa_sdk -v

generate-pending-changelog:
	poetry run python -c "from scripts import release; release.generate_changelog('major.minor.patch')"

cleanup-generated-changelog:
	# this is a helper to cleanup your git status locally after running "make test-docs"
	# it's not run on CI at the moment
	git status --porcelain | sed -n '/^D */s///p' | xargs git reset HEAD
	git reset HEAD CHANGELOG.mdx
	git ls-files --deleted | xargs git checkout
	git checkout CHANGELOG.mdx

release:
	poetry run python scripts/release.py

download-protoc-compiler:
	curl -0L https://github.com/protocolbuffers/protobuf/releases/download/v25.0/protoc-25.0-osx-aarch_64.zip --output protoc-25.0-osx-aarch_64.zip

generate-grpc:
	 python -m grpc_tools.protoc \
	 	-Irasa_sdk/grpc_py=./proto \
	 	--python_out=. \
	 	--grpc_python_out=. \
	 	--pyi_out=. \
	 	proto/action_webhook.proto