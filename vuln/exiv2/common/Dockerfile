FROM ghcr.io/cla7aye15i4nd/patchagent:v2.1.0

RUN git clone https://github.com/Exiv2/exiv2.git /repo

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y \
    build-essential \
    cmake \
    gcc-9 \
    g++-9 \
    libexpat1-dev \
    zlib1g-dev \
    libssh-dev \
    libcurl4-openssl-dev \
    libgtest-dev \
    libinih-dev \
    libxml2-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY cold /workspace/cold

ENTRYPOINT [ "python", "-m", "cold.cli" ]