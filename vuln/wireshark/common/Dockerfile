FROM ghcr.io/cla7aye15i4nd/patchagent:v2.1.0

RUN git clone https://github.com/wireshark/wireshark.git /repo

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y \
    build-essential \
    lemon \
    && rm -rf /var/lib/apt/lists/*

RUN sed -i 's/apt-get install /apt-get install -y /' /repo/tools/debian-setup.sh && \
    DEBIAN_FRONTEND=noninteractive /repo/tools/debian-setup.sh --install-all

RUN cd /repo && \
    git restore tools/debian-setup.sh

WORKDIR /workspace

COPY cold /workspace/cold

ENTRYPOINT [ "python", "-m", "cold.cli" ]