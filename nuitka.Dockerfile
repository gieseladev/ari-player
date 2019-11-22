# This is a image which tries to compile Ari using Nuitka to run in a scratch
# container. Not in a working state

FROM python:3.7 as builder

RUN pip install --upgrade \
    pipenv \
    nuitka

COPY Pipfile .
COPY Pipfile.lock .

RUN pipenv install --system --deploy --dev

WORKDIR /ari

COPY ari/ ./ari

# compile using Nuitka
RUN python -m nuitka \
    --warn-implicit-exceptions --warn-unusual-code \
    --show-scons --show-progress --show-modules \
    --follow-imports --python-flag=no_site \
    --trace-execution \
    ari/cli.py

ENTRYPOINT bash
