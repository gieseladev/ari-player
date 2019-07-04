FROM python:3-slim

WORKDIR /ari-build

RUN pip install --upgrade pipenv

COPY Pipfile ./
COPY Pipfile.lock ./

RUN pipenv install --system --deploy

WORKDIR /
RUN rm --recursive /ari-build

COPY ari/ /ari/

RUN touch /config.toml

ENTRYPOINT ["python", "-m", "ari.cli", "--config", "/config.toml"]