FROM debian:trixie-slim

# Install utilities
USER root
RUN apt-get update -y && apt-get install -y curl gcc git libssl-dev pkgconf tar && apt-get clean

# Switch to default user
RUN useradd -ms /bin/bash dev
USER dev 

# Install rust 
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/home/dev/.cargo/bin:${PATH}"
RUN rustup update
