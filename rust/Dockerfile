FROM adregistry.fnal.gov/dev-containers/redhat-ubi9-minimal

# Install utilities
USER root
RUN microdnf update -y && microdnf install -y --allowerasing cmake curl gcc gcc-c++ git libcurl-devel pkgconf sudo tar && microdnf clean -y

# Switch to default user
RUN useradd -G wheel dev
# Grant passwordless sudo permissions to the wheel group
RUN echo "%wheel ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/wheel \
    && chmod 0440 /etc/sudoers.d/wheel
USER dev 

# Install rust 
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/home/dev/.cargo/bin:${PATH}"
RUN rustup update
