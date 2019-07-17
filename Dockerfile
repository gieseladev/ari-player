FROM python:3 as builder

RUN apt-get update && apt-get install -y \
    chrpath

RUN pip install --upgrade \
    pipenv \
    "https://github.com/Nuitka/Nuitka/archive/develop.zip"

COPY Pipfile .
COPY Pipfile.lock .

RUN pipenv install --system --deploy

WORKDIR /ari

COPY ari/ ./ari

# compile using Nuitka
RUN python -m nuitka \
    --show-scons --show-progress --show-modules \
    --standalone --python-flag=no_site \
    ari/cli.py

# copy dynamic dependencies into the dist directory
RUN APP="cli.dist/cli" ; \
    COPY_TO="cli.dist" ; \
    ldd ${APP} | grep "=> /" | awk '{print $3}' | xargs -I '{}' cp --no-clobber -v '{}' ${COPY_TO} && \
    ldd ${APP} | grep "/lib64/ld-linux-x86-64" | awk '{print $1}' | xargs -I '{}' cp --parents -v '{}' ${COPY_TO} && \
    cp --no-clobber -v /lib/x86_64-linux-gnu/libgcc_s.so.1 ${COPY_TO}


FROM scratch
LABEL version="0.0.1"

COPY --from=builder /ari/cli.dist/ /

ENTRYPOINT ["/cli"]
