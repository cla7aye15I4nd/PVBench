FROM ghcr.io/cla7aye15i4nd/patchagent:v2.1.0

RUN git clone https://github.com/simdjson/simdjson.git /repo

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y \
    build-essential \
    cmake \
    g++ \
    make \
    zip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY cold /workspace/cold

ENTRYPOINT [ "python", "-m", "cold.cli" ]