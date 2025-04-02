FROM ubuntu:22.04 AS base

# hadolint ignore=DL3005,DL3008
RUN apt-get update -qq \
    # Make sure that all security updates are installed
    && apt-get dist-upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
      python3 \
      python3-venv \
      python3-pip \
      python3-dev \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 100 \
   && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 100

FROM base AS python_builder

ARG POETRY_VERSION=2.0.0

# hadolint ignore=DL3008
RUN apt-get update -qq \
   && apt-get install -y --no-install-recommends \
    curl \
    && apt-get autoremove -y

# install poetry
# keep this in sync with the version in pyproject.toml and Dockerfile
ENV POETRY_VERSION=$POETRY_VERSION
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -sSL https://install.python-poetry.org | python
ENV PATH="/root/.local/bin:/opt/venv/bin:${PATH}"

# install dependencies
COPY . /app/

WORKDIR /app

# hadolint ignore=SC1091,DL3013
RUN python -m venv /opt/venv && \
  . /opt/venv/bin/activate && \
  pip install --no-cache-dir -U pip && \
  pip install --no-cache-dir wheel && \
  poetry install --no-dev --no-root --no-interaction

# install dependencies and build wheels
# hadolint ignore=SC1091,DL3013
RUN . /opt/venv/bin/activate && poetry build -f wheel -n \
  && pip install --no-cache-dir --no-deps dist/*.whl \
  && mkdir /wheels \
  && poetry export -f requirements.txt --without-hashes --output /wheels/requirements.txt \
  && poetry run pip wheel --wheel-dir=/wheels -r /wheels/requirements.txt \
  && find /app/dist -maxdepth 1 -mindepth 1 -name '*.whl' -print0 | xargs -0 -I {} mv {} /wheels/

WORKDIR /wheels
# install wheels
# hadolint ignore=SC1091,DL3013
RUN find . -name '*.whl' -maxdepth 1 -exec basename {} \; | awk -F - '{ gsub("_", "-", $1); print $1 }' | uniq > /wheels/requirements.txt \
  && rm -rf /opt/venv \
  && python -m venv /opt/venv \
  && . /opt/venv/bin/activate \
  && pip install --no-cache-dir -U pip \
  && pip install --no-cache-dir --no-index --find-links=/wheels -r /wheels/requirements.txt \
  && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
  && rm -rf /wheels \
  && rm -rf /root/.cache/pip/*

# final image
FROM base

# copy needed files
COPY ./entrypoint.sh /app/
COPY --from=python_builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

# update permissions & change user
RUN chgrp -R 0 /app && chmod -R g=u /app
USER 1001

# change shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# create a mount point for custom actions and the entry point
WORKDIR /app
EXPOSE 5055
ENTRYPOINT ["./entrypoint.sh"]
CMD ["start", "--actions", "actions"]
