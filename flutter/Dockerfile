FROM adregistry.fnal.gov/dev-containers/redhat-ubi9-minimal

# Install tools
USER root
RUN microdnf update -y && \
    microdnf install -y findutils git jq sudo tar unzip which xz && \
    microdnf clean all

ENV FLUTTER_HOME=/usr/local/flutter
ENV PATH="$FLUTTER_HOME/bin:$PATH"

RUN FLUTTER_ARCHIVE=$(curl -s https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json \
    | jq -r '.releases[] | select(.channel=="stable") | .archive' | head -n 1) && \
    curl -L "https://storage.googleapis.com/flutter_infra_release/releases/$FLUTTER_ARCHIVE" \
    | tar -xJ -C /usr/local && \
    git config --global --add safe.directory /usr/local/flutter

RUN useradd -G wheel dev
# Grant passwordless sudo permissions to the wheel group
RUN echo "%wheel ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/wheel \
    && chmod 0440 /etc/sudoers.d/wheel

# Change to default user
USER dev

# Disable telemetry
RUN flutter --disable-analytics

# Install flutter bash completion
RUN mkdir ~/.bash-completion -p
RUN flutter bash-completion > ~/.bash-completion/flutter
RUN chmod +x ~/.bash-completion/flutter

# Source flutter bash completion
RUN echo 'source ~/.bash-completion/flutter' >> ~/.bashrc
