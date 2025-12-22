FROM ghcr.io/cla7aye15i4nd/patchagent:v2.1.0

RUN git clone https://github.com/jasper-software/jasper.git /repo

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y \
    build-essential \
    cmake \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libopenjp2-7-dev \
    freeglut3-dev \
    libglew-dev \
    libglu1-mesa-dev \
    libxi-dev \
    libheif-dev \
    libxmu-dev \
    doxygen \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY cold /workspace/cold

ENTRYPOINT [ "python", "-m", "cold.cli" ]