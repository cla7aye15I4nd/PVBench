FROM ghcr.io/cla7aye15i4nd/patchagent:v2.1.0

RUN git clone https://github.com/WebAssembly/wabt.git /repo --recursive

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y \
    build-essential \
    cmake \
    python3 \
    ninja-build \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY cold /workspace/cold

ENTRYPOINT [ "python", "-m", "cold.cli" ]