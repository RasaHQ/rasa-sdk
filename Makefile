.PHONY: clean test lint init check-readme docs

TEST_PATH=./
INTEGRATION_TEST_FOLDER = integration_tests
GRPC_SERVER_INTEGRATION_TEST_FOLDER = $(INTEGRATION_TEST_FOLDER)/grpc_server

help:  ## show help message
	@grep -hE '^[A-Za-z0-9_ \-]*?:.*##.*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: ## install dependencies (pip will resolve protobuf version)
	poetry run python -m pip install -U pip
	poetry install -vv

install-protobuf4: ## install dependencies but force protobuf 4.25.8
	poetry run python -m pip install -U pip
	poetry add "protobuf==4.25.8"
	poetry install -vv

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
	poetry run ruff format rasa_sdk tests

lint: ## check style with ruff and black
	poetry run ruff check rasa_sdk tests --ignore D
	poetry run ruff format --check rasa_sdk tests
	make lint-docstrings
	make check-generate-grpc-code-in-sync

 # Compare against `main` if no branch was provided
BRANCH ?= main
lint-docstrings: ## check docstrings
	./scripts/lint_python_docstrings.sh $(BRANCH)

IMAGE_NAME ?= rasa/rasa-sdk
IMAGE_WITH_DEV_DEPS ?= rasa/rasa-sdk-with-dev-deps
IMAGE_TAG ?= latest
PLATFORM ?= linux/arm64
POETRY_VERSION ?= $(shell ./scripts/poetry-version.sh)

# Builds a docker image with runtime dependencies installed
build-docker:  ## build docker image for one platform
	docker build . \
			--build-arg POETRY_VERSION=$(POETRY_VERSION) \
            --platform=$(PLATFORM) \
            -f Dockerfile \
            -t $(IMAGE_NAME):$(IMAGE_TAG)

# Builds a docker image with runtime and dev dependencies installed
build-docker-with-dev-deps:  ## build docker image with dev dependencies for one platform
	docker build . \
			--build-arg POETRY_VERSION=$(POETRY_VERSION) \
            --platform=$(PLATFORM) \
            -f Dockerfile.dev \
            -t $(IMAGE_WITH_DEV_DEPS):$(IMAGE_TAG)

# To be able to build a multiplatform docker image
# make sure that builder with appropriate docker driver is enabled and set as current builder
build-and-push-multi-platform-docker: PLATFORM = linux/amd64,linux/arm64
build-and-push-multi-platform-docker:  ## build and push multi-platform docker image
	docker buildx build . \
            --build-arg POETRY_VERSION=$(POETRY_VERSION) \
			--platform=$(PLATFORM) \
			-f Dockerfile \
			-t $(IMAGE_NAME):$(IMAGE_TAG) \
			-t $(IMAGE_NAME):$(IMAGE_TAG)-latest \
			--push

# To be able to build a multiplatform docker image with dev dependencies
# make sure that builder with appropriate docker driver is enabled and set as current builder
build-and-push-multi-platform-docker-with-dev-deps: PLATFORM = linux/amd64,linux/arm64
build-and-push-multi-platform-docker-with-dev-deps:  ## build and push multi-platform docker image with dev dependencies
	docker buildx build . \
            --build-arg POETRY_VERSION=$(POETRY_VERSION) \
			--platform=$(PLATFORM) \
			-f Dockerfile.dev \
			-t $(IMAGE_WITH_DEV_DEPS):$(IMAGE_TAG) \
			--push

test: clean  ## run tests
	poetry run \
		pytest tests \
			--cov rasa_sdk \
			-v

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

tag-release:  ## Tag a release.
	poetry run python scripts/release.py --tag

generate-grpc:  ## generate grpc code
	make generate-grpc-pb4
	make generate-grpc-pb5

generate-grpc-pb4:
	poetry add "protobuf==4.25.8"
	poetry run python -m grpc_tools.protoc \
		-Irasa_sdk/grpc_py/pb4=./proto \
		--python_out=. \
		--grpc_python_out=. \
		--pyi_out=. \
		proto/action_webhook.proto

generate-grpc-pb5:
	poetry add "protobuf==5.29.5"
	poetry run python -m grpc_tools.protoc \
		-Irasa_sdk/grpc_py/pb5=./proto \
		--python_out=. \
		--grpc_python_out=. \
		--pyi_out=. \
		proto/action_webhook.proto

check-generate-grpc-code-in-sync: generate-grpc ## check if the generated code is in sync with the proto files, it uses a helper to check if the generated code is in sync with the proto files
	git diff --exit-code rasa_sdk/grpc_py | if [ "$$(wc -c)" -eq 0 ]; then echo "Generated code is in sync with proto files"; else echo "Generated code is not in sync with proto files"; exit 1; fi

GRPC_STANDALONE_SERVER_INTEGRATION_TEST_RESULTS_FILE = grpc-standalone-server-integration-test-results.xml

run-grpc-standalone-integration-tests: ## run the grpc standalone integration tests
	docker run --rm \
		-v $(PWD):/app \
		$(IMAGE_WITH_DEV_DEPS):$(IMAGE_TAG) \
		poetry run \
			pytest $(INTEGRATION_TEST_FOLDER)/test_standalone_grpc_server.py \
			--junitxml=$(GRPC_STANDALONE_SERVER_INTEGRATION_TEST_RESULTS_FILE) \
			--verbose

GRPC_SERVER_DOCKER_COMPOSE_FILE = $(GRPC_SERVER_INTEGRATION_TEST_FOLDER)/setup/docker-compose.yml

start-grpc-integration-test-env: ## run the rnv for the grpc integration tests
	RASA_SDK_REPOSITORY=$(IMAGE_NAME) \
	RASA_SDK_IMAGE_TAG=$(IMAGE_TAG) \
	docker compose -f $(GRPC_SERVER_DOCKER_COMPOSE_FILE) up --wait

stop-grpc-integration-test-env: ## stop the env for the grpc integration tests
	RASA_SDK_REPOSITORY=$(IMAGE_NAME) \
	RASA_SDK_IMAGE_TAG=$(IMAGE_TAG) \
	docker compose -f $(GRPC_SERVER_DOCKER_COMPOSE_FILE) down

GRPC_SERVER_DOCKER_INTEGRATION_TEST_RESULTS_FILE = grpc-server-docker-integration-test-results.xml

# Runs the gRPC integration tests in a docker container created from the image with dev dependencies
# Make sure to first start the environment with `make start-grpc-integration-test-env` before running this target
run-grpc-integration-tests: ## run the grpc integration tests
	docker run --rm \
		-v $(PWD):/app \
		--network setup_rasa-pro-network \
		-e GRPC_ACTION_SERVER_HOST="action-server-grpc-no-tls" \
		-e GRPC_ACTION_SERVER_TLS_HOST="action-server-grpc-tls" \
		$(IMAGE_WITH_DEV_DEPS):$(IMAGE_TAG) \
		poetry run \
			pytest $(GRPC_SERVER_INTEGRATION_TEST_FOLDER)/test_docker_grpc_server.py \
			--junitxml=$(GRPC_SERVER_DOCKER_INTEGRATION_TEST_RESULTS_FILE) \
			--verbose
