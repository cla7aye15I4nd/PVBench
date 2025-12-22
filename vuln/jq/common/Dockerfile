FROM ghcr.io/cla7aye15i4nd/patchagent:v2.1.0

RUN git clone --recursive https://github.com/jqlang/jq.git /repo

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y \
    libtool \
    make \
    automake \
    autoconf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY cold /workspace/cold

ENTRYPOINT [ "python", "-m", "cold.cli" ]