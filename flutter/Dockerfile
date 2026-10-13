FROM adregistry.fnal.gov/dev-containers/redhat-ubi9-minimal

# Install tools
USER root
RUN microdnf update -y && \
    microdnf install -y findutils git sudo tar unzip which && \
    microdnf clean all

# Set up users and groups
RUN useradd -G wheel dev && \
    echo "%wheel ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/wheel && \
    chmod 0440 /etc/sudoers.d/wheel

# Flutter release to install; also the image version tag.
ARG FLUTTER_VERSION=3.47.7

# Configure Flutter location and env vars
ENV FLUTTER_HOME=/home/dev/flutter
ENV PATH="$FLUTTER_HOME/bin:$PATH"

# Change to default user
USER dev

# Pull flutter, enable it to be used during CI/CD (git config ...), and turn off analytics.
# Then configure the dev user's .bashrc to use the flutter bash completion.
# Cloning a release tag leaves a detached HEAD; name the branch 'stable' so Flutter reports its channel.
RUN git clone --depth 1 -b "$FLUTTER_VERSION" https://github.com/flutter/flutter.git $FLUTTER_HOME && \
    git -C $FLUTTER_HOME switch -c stable && \
    git config --global --add safe.directory $FLUTTER_HOME && \
    flutter --disable-analytics && dart --disable-analytics && \
    mkdir ~/.bash-completion -p && \
    flutter bash-completion > ~/.bash-completion/flutter && \
    chmod +x ~/.bash-completion/flutter && \
    echo 'source ~/.bash-completion/flutter' >> ~/.bashrc
