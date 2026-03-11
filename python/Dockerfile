FROM redhat/ubi9-minimal

# Install utilities
USER root
RUN microdnf update -y && microdnf install -y gcc git openssl-devel pkgconf tar vim && microdnf clean all

# Switch to default user
RUN adduser dev
USER dev

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/dev/.cargo/bin:/home/dev/.local/bin:${PATH}"

# Install Python 3.12
RUN uv python install 3.12
