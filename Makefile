.PHONY: clean test lint init check-readme docs

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

install:
	poetry install
	yarn install

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
	yarn typecheck

lint:
	poetry run flake8 rasa_sdk tests
	poetry run black --check rasa_sdk tests

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

docs:
	cd docs/ && poetry run yarn pre-build && yarn build

test-docs: generate-pending-changelog docs

livedocs:
	cd docs/ && poetry run yarn start

release:
	poetry run python scripts/release.py

