FROM ghcr.io/cla7aye15i4nd/patchagent:v2.1.0

RUN git clone https://chromium.googlesource.com/v8/v8.git /repo
RUN git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git /depot_tools
ENV PATH=/depot_tools:$PATH
RUN ensure_bootstrap

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get install -y \
        bear \
        rsync \
        libclang-rt-dev \
        ninja-build \ 
        python3.11 \
        llvm && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install openai-agents SDK for test generation with feedback loop
RUN pip install openai-agents pydantic

COPY cold /workspace/cold

ENTRYPOINT [ "python", "-m", "cold.cli" ]