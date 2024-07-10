.PHONY: clean test lint init check-readme docs

TEST_PATH=./

help:  ## show help message
	@grep -E '^[a-z.A-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: ## install dependencies
	poetry run python -m pip install -U pip
	poetry install

install-dev: ## install dependencies for development
	poetry run python -m pip install -U pip
	poetry install --with dev

clean: ## remove all build, test, coverage and Python artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f  {} +
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info

types: ## check types
	poetry run mypy rasa_sdk

formatter: ## format code
	poetry run black rasa_sdk tests

lint: ## check style with ruff and black
	poetry run ruff check rasa_sdk tests --ignore D
	poetry run black --exclude="rasa_sdk/grpc_py" --check rasa_sdk tests
	make lint-docstrings
	make check-generate-grpc-code-in-sync

 # Compare against `main` if no branch was provided
BRANCH ?= main
lint-docstrings: ## check docstrings
	./scripts/lint_python_docstrings.sh $(BRANCH)

IMAGE_NAME ?= rasa/rasa-sdk
IMAGE_TAG ?= latest
PLATFORM ?= linux/arm64
POETRY_VERSION ?= $(shell ./scripts/poetry-version.sh)

build-docker:  ## build docker image for one platform
	docker build . \
			--build-arg POETRY_VERSION=$(POETRY_VERSION) \
            --platform=$(PLATFORM) \
            -f Dockerfile \
            -t $(IMAGE_NAME):$(IMAGE_TAG)

# To be able to build a multiplatform docker image
# make sure that builder with appropriate docker driver is enabled and set as current
build-and-push-multi-platform-docker: PLATFORM = linux/amd64,linux/arm64
build-and-push-multi-platform-docker:  ## build and push multi-platform docker image
	docker buildx build . \
            --build-arg POETRY_VERSION=$(POETRY_VERSION) \
			--platform=$(PLATFORM) \
			-f Dockerfile \
			-t $(IMAGE_NAME):$(IMAGE_TAG) \
			--push

test: clean  ## run tests
	poetry run py.test tests --cov rasa_sdk -v

generate-pending-changelog:  ## generate a changelog for the next release
	poetry run python -c "from scripts import release; release.generate_changelog('major.minor.patch')"

cleanup-generated-changelog:  ## cleanup the generated changelog
	# this is a helper to cleanup your git status locally after running "make test-docs"
	# it's not run on CI at the moment
	git status --porcelain | sed -n '/^D */s///p' | xargs git reset HEAD
	git reset HEAD CHANGELOG.mdx
	git ls-files --deleted | xargs git checkout
	git checkout CHANGELOG.mdx

release: ## start the release process
	poetry run python scripts/release.py

generate-grpc:  ## generate grpc code
	 poetry run python -m grpc_tools.protoc \
	 	-Irasa_sdk/grpc_py=./proto \
	 	--python_out=. \
	 	--grpc_python_out=. \
	 	--pyi_out=. \
	 	proto/action_webhook.proto \
	 	proto/health.proto

check-generate-grpc-code-in-sync: generate-grpc
check-generate-grpc-code-in-sync: ## check if the generated code is in sync with the proto files
	# this is a helper to check if the generated code is in sync with the proto files
	# it's not run on CI at the moment
	git diff --exit-code rasa_sdk/grpc_py | if [ "$$(wc -c)" -eq 0 ]; then echo "Generated code is in sync with proto files"; else echo "Generated code is not in sync with proto files"; exit 1; fi