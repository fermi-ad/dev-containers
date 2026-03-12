FROM redhat/ubi9-minimal

# Install utilities
USER root
RUN microdnf update -y && microdnf install -y cmake gcc gcc-c++ git kernel-tools libcurl-devel librdkafka-devel openssl-devel pkgconf tar && microdnf clean all

# Switch to default user
RUN adduser dev
USER dev 

# Install rust 
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/home/dev/.cargo/bin:${PATH}"
RUN rustup update 
