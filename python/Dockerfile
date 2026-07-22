FROM redhat/ubi9-minimal

# Install utilities
USER root
RUN microdnf update -y && microdnf install -y gcc git openssl-devel pkgconf sudo tar vim && microdnf clean all

# Switch to default user
RUN adduser dev
RUN usermod --append -G wheel dev
# Grant passwordless sudo permissions to the wheel group
RUN echo "%wheel ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/wheel \
    && chmod 0440 /etc/sudoers.d/wheel
USER dev

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/dev/.local/bin:${PATH}"

# Install Python 3.12
RUN uv python install 3.12
