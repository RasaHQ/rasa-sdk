# Rasa Python-SDK
[![Join the chat on Rasa Community Forum](https://img.shields.io/badge/forum-join%20discussions-brightgreen.svg)](https://forum.rasa.com/?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![Build Status](https://github.com/RasaHQ/rasa-sdk/workflows/Continous%20Integration/badge.svg?event=push)](https://github.com/RasaHQ/rasa-sdk/actions/runs/)
[![Coverage Status](https://coveralls.io/repos/github/RasaHQ/rasa-sdk/badge.svg?branch=main)](https://coveralls.io/github/RasaHQ/rasa-sdk?branch=main)
[![PyPI version](https://img.shields.io/pypi/v/rasa-sdk.svg)](https://pypi.python.org/pypi/rasa-sdk)

Python SDK for the development of custom actions for Rasa.

<hr />

💡 **We're migrating issues to Jira** 💡

Starting January 2023, issues for Rasa Open Source are located in
[this Jira board](https://rasa-open-source.atlassian.net/browse/OSS). You can browse issues without being logged in;
if you want to create issues, you'll need to create a Jira account.

<hr />

## Installation

To install the SDK run

```bash
pip install rasa-sdk
```

## Compatibility

`rasa-sdk` package:

| SDK version    | compatible Rasa version           |
|----------------|-----------------------------------|
| `1.0.x`        | `>=1.0.x`                         |

old `rasa_core_sdk` package:

| SDK version    | compatible Rasa Core version           |
|----------------|----------------------------------------|
| `0.12.x`       | `>=0.12.x`                             |
| `0.11.x`       | `0.11.x`                               |
| not compatible | `<=0.10.x`                             |

## Usage

Detailed instructions can be found in the Rasa Documentation about
[Custom Actions](https://rasa.com/docs/rasa/core/actions).

## Docker

### Usage

In order to start an action server using implemented custom actions,
you can use the available Docker image `rasa/rasa-sdk`.

Before starting the action server ensure that the folder containing
your actions is handled as Python module and therefore has to contain
a file called `__init__.py`

Then start the action server using:

```bash
docker run -p 5055:5055 --mount type=bind,source=<ABSOLUTE_PATH_TO_YOUR_ACTIONS>,target=/app/actions \
	rasa/rasa-sdk:<version>
```

The action server is then available at `http://localhost:5055/webhook`.

### Custom Dependencies

To add custom dependencies you enhance the given Docker image, e.g.:

```
# Extend the official Rasa SDK image
FROM rasa/rasa-sdk:<version>

# Change back to root user to install dependencies
USER root

# To install system dependencies
RUN apt-get update -qq && \
    apt-get install -y <NAME_OF_REQUIRED_PACKAGE> && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# To install packages from PyPI
RUN pip install --no-cache-dir <A_REQUIRED_PACKAGE_ON_PYPI>

# Switch back to non-root to run code
USER 1001
```

## Building from source

Rasa SDK uses Poetry for packaging and dependency management. If you want to build it from source,
you have to install Poetry first. This is how it can be done:

```
curl -sSL https://install.python-poetry.org | python3 -
```

There are several other ways to install Poetry. Please, follow
[the official guide](https://python-poetry.org/docs/#installation) to see all possible options.

To install dependencies and `rasa-sdk` itself in editable mode execute
```
make install
```

## Code Style

To ensure a standardized code style we use the formatter [ruff](https://github.com/astral-sh/ruff).
If your code is not formatted properly, GitHub CI will fail to build.

If you want to automatically format your code on every commit, you can use [pre-commit](https://pre-commit.com/).
Just install it via `pip install pre-commit` and execute `pre-commit install`.

To check and reformat files execute
```
make lint
```

## Steps to release a new version
Releasing a new version is quite simple, as the packages are build and distributed
by GitHub Actions.

*Release steps*:
1. Switch to the branch you want to cut the release from (`main` in case of a
  major / minor, the current release branch for patch releases).
2. If this is a minor / major release: Make sure all fixes from currently supported minor versions have been merged from their respective release branches (e.g. 3.3.x) back into main.
3. Run `make release`
4. Create a PR against main or the release branch (e.g. `1.2.x`)
5. **If this is a minor release**, a new release branch should be created
  pointing to the same commit as the tag to allow for future patch releases,
  e.g.
    ```bash
    git checkout -b 1.2.x
    git push origin 1.2.x
    ```

## License
Licensed under the Apache License, Version 2.0. Copyright 2021 Rasa
Technologies GmbH. [Copy of the license](LICENSE.txt).

A list of the Licenses of the dependencies of the project can be found at
the bottom of the
[Libraries Summary](https://libraries.io/github/RasaHQ/rasa-sdk).
