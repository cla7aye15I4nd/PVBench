FROM ghcr.io/cla7aye15i4nd/patchagent:v2.1.0

RUN git clone https://gitlab.gnome.org/GNOME/libxml2.git /repo

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y \
    build-essential \
    cmake \
    wget \
    pkg-config \
    autotools-dev \
    automake \
    libtool \
    zlib1g-dev \
    liblzma-dev \
    libicu-dev \
    python3-dev \
    python3-setuptools \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3-config /usr/bin/python-config && \
    pip install setuptools

WORKDIR /workspace

COPY cold /workspace/cold

ENTRYPOINT [ "python", "-m", "cold.cli" ]