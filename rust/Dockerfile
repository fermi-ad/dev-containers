# Rust toolchain to install; also the image version tag.
ARG RUST_VERSION=1.99.1

FROM adregistry.fnal.gov/dev-containers/redhat-ubi9-minimal

# Redeclare for use inside this block
ARG RUST_VERSION

# Install utilities
USER root
# Update, install build tools, swap curl-minimal, and clean up in one layer
RUN microdnf update -y && microdnf install -y \
    cmake \
    gcc \
    gcc-c++ \
    git \
    libssh \
    libpsl \
    libbrotli \
    pkgconf \
    sudo \
    tar \
    && microdnf download -y curl libcurl libcurl-devel \
    && rpm -Uvh --nodeps --replacefiles curl-*.rpm libcurl-*.rpm libcurl-devel-*.rpm \
    && rm -f *.rpm \
    && microdnf clean all

# Switch to default user
RUN useradd -G wheel dev
# Grant passwordless sudo permissions to the wheel group
RUN echo "%wheel ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/wheel \
    && chmod 0440 /etc/sudoers.d/wheel
USER dev

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain "$RUST_VERSION"
ENV PATH="/home/dev/.cargo/bin:${PATH}"

# Install coverage tools
RUN cargo install cargo-llvm-cov && \
    rustup component add llvm-tools-preview && \
    rm -rf /home/dev/.cargo/registry && \
    rm -rf /home/dev/.cargo/git
