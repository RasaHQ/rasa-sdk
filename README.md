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

### Add Sanic extensions
With the use of Pluggy, you can now create additional sanic extensions by accessing the app object created by the action server.

#### Step by Step Guide on creating your own sanic extension in rasa_sdk
This example will show how to create a sanic listener using plugins

##### Step 1
Create a package in your action server project called `rasa_sdk_plugins`. Rasa SDK will try to instantiate this package in your project to start plugins.
If no plugins found, it will print an info that there are no plugins in your project.

##### Step 2
Instantiate the package rasa_sdk_plugins and initialise the hooks. create an `__init__.py` Plugin manager will look for the module where the hooks are implemented

```
def init_hooks(manager: pluggy.PluginManager) -> None:
    """Initialise hooks into rasa sdk."""
    import sys
    logger.info("Finding hooks")
    manager.register(sys.modules["rasa_sdk_plugins.your_module"])
```
##### Step 3
Implement the hook `attach_sanic_app_extensions`. this hook forwards the app object created by sanic in the rasa_sdk and allows you to create additional routes, middlewares, listeners and background tasks. Here's an example of this implementation that creates a listener.

In your `rasa_sdk_plugins.module.py`

```
from __future__ import annotations
import logging

import pluggy

from functools import partial

logger = logging.getLogger(__name__)
hookimpl = pluggy.HookimplMarker("rasa_sdk")

@hookimpl  # type: ignore[misc]
def attach_sanic_app_extensions(app) -> bool:
    logger.info("hook called")
    app.register_listener(
        partial(print),
        "before_server_start",
    )
    return app

async def print(app, loop):
    logger.info("BEFORE SERVER START")
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

To ensure a standardized code style we use the formatter [black](https://github.com/ambv/black).
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
5. Once your PR is merged, pull the release branch locally.
6. Create a tag for a new release (this SHOULD always happen on `main` or release branches), e.g. using
    ```bash
    git tag 1.2.0 -m "next release"
    git push origin 1.2.0
    ```
    GitHub Actions will build this tag and push a package to
    [pypi](https://pypi.python.org/pypi/rasa-sdk).
6. **If this is a minor release**, a new release branch should be created
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
