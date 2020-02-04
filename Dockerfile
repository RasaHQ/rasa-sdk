FROM python:3.6-alpine as python_builder
RUN apk update && \
  apk add \
  build-base \
  curl \
  git

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
ENV PATH "/root/.poetry/bin:/opt/venv/bin:${PATH}"

COPY poetry.lock pyproject.toml /opt/project/
RUN python -m venv /opt/venv && \
  source /opt/venv/bin/activate && \
  pip install -U pip && \
  cd /opt/project && \
  poetry install --no-dev --no-interaction

COPY . /opt/project
RUN source /opt/venv/bin/activate && \
  cd /opt/project && \
  poetry install --no-dev --no-interaction

FROM python:3.6-alpine
RUN apk update && apk add bash

COPY --from=python_builder /opt /opt
ENV PATH="/opt/venv/bin:$PATH"
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

VOLUME ["/app/actions"]
EXPOSE 5055

ENTRYPOINT ["./opt/project/entrypoint.sh"]

CMD ["start", "--actions", "actions.actions"]
