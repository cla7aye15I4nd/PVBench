FROM ghcr.io/cla7aye15i4nd/patchagent:v2.1.0

RUN git clone https://github.com/python/cpython.git /repo

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y \
    libcurl4-openssl-dev \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libffi-dev \
    libsqlite3-dev \
    libreadline-dev \
    libbz2-dev \
    liblzma-dev \
    libncurses-dev \
    tk-dev \
    libgdbm-dev \
    libdb-dev \
    libnss3-dev \
    libexpat1-dev \
    libzstd-dev \
    uuid-dev \
    xvfb && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install openai-agents SDK for test generation with feedback loop
RUN pip install openai-agents pydantic

COPY cold /workspace/cold

ENTRYPOINT [ "python", "-m", "cold.cli" ]