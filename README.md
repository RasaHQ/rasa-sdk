# Rasa Python-SDK
[![Join the chat on Rasa Community Forum](https://img.shields.io/badge/forum-join%20discussions-brightgreen.svg)](https://forum.rasa.com/?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![Build Status](https://travis-ci.com/RasaHQ/rasa-sdk.svg?branch=master)](https://travis-ci.com/RasaHQ/rasa-sdk)
[![PyPI version](https://img.shields.io/pypi/v/rasa-sdk.svg)](https://pypi.python.org/pypi/rasa-sdk)
[![Documentation Status](https://img.shields.io/badge/docs-stable-brightgreen.svg)](https://rasa.com/docs)

Python SDK for the development of custom actions for Rasa.

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
[Custom Actions](https://rasa.com/docs/rasa/core/run-code-in-custom-actions/).

## Docker

### Usage

In order to start an action server using implemented custom actions,
you can use the available Docker image `rasa/rasa-sdk:latest`.

Before starting the action server ensure that the folder containing
your actions is handled as Python module and therefore has to contain
a file called `__init__.py`

Then start the action server using:

```bash
docker run -p 5055:5055 --mount type=bind,source=<ABSOLUTE_PATH_TO_YOUR_ACTIONS>,target=/app/actions \
	rasa/rasa-sdk:latest
```

The action server is then available at `http://localhost:5055/webhook`.

### Custom Dependencies

To add custom dependencies you enhance the given Docker image, e.g.:

```
FROM rasa/rasa-sdk:latest

# To install system dependencies
RUN apt-get update -qq && \
    apt-get install -y <NAME_OF_REQUIRED_PACKAGE> && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# To install packages from PyPI
RUN pip install --no-cache-dir <A_REQUIRED_PACKAGE_ON_PYPI>
```

## Code Style

To ensure a standardized code style we use the formatter [black](https://github.com/ambv/black).
If your code is not formatted properly, travis will fail to build.

If you want to automatically format your code on every commit, you can use [pre-commit](https://pre-commit.com/).
Just install it via `pip install pre-commit` and execute `pre-commit install`.

If you want to set it up manually, install black via `pip install black`.
To reformat files execute
```
black .
```


## License
Licensed under the Apache License, Version 2.0. Copyright 2019 Rasa
Technologies GmbH. [Copy of the license](LICENSE.txt).

A list of the Licenses of the dependencies of the project can be found at
the bottom of the
[Libraries Summary](https://libraries.io/github/RasaHQ/rasa-sdk).
