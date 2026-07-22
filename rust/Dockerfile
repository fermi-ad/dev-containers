FROM debian:trixie-slim

# Install utilities
USER root
RUN apt-get update -y && apt-get install -y cmake curl gcc g++ git libcurl4-openssl-dev pkgconf sudo tar && apt-get clean -y

# Switch to default user
RUN useradd -ms /bin/bash dev
# Grant passwordless sudo permissions to the dev user
RUN echo "dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dev \
    && chmod 0440 /etc/sudoers.d/dev
USER dev 

# Install rust 
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/home/dev/.cargo/bin:${PATH}"
RUN rustup update
