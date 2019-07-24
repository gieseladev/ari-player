FROM python:3.7 as builder

RUN pip install pipenv

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY Pipfile .
COPY Pipfile.lock .

RUN pipenv install --deploy --system


FROM python:3.7-slim
LABEL version="0.0.1"

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY ari/ /ari

ENTRYPOINT ["python", "-m", "ari.cli"]