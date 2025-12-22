FROM ghcr.io/cla7aye15i4nd/patchagent:v2.1.0

RUN git clone https://github.com/mruby/mruby.git /repo

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y \
    build-essential \
    flex \
    bison \
    libssl-dev \
    ruby \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install openai-agents SDK for test generation with feedback loop
RUN pip install openai-agents pydantic

COPY cold /workspace/cold

ENTRYPOINT [ "python", "-m", "cold.cli" ]