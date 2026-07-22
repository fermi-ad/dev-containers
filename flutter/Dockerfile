FROM redhat/ubi9-minimal

# Install tools
USER root
RUN microdnf update -y && microdnf install -y unzip git findutils which tar sudo && microdnf clean all
RUN useradd dev
RUN usermod --append -G wheel dev
# Grant passwordless sudo permissions to the wheel group
RUN echo "%wheel ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/wheel \
    && chmod 0440 /etc/sudoers.d/wheel
RUN mkdir /flutter && chown -R dev /flutter

# Change to default user
USER dev

# Get latest Flutter
RUN git clone -v -b stable https://github.com/flutter/flutter /flutter
ENV PATH="/flutter/bin:${PATH}"

# Disable telemetry
RUN flutter --disable-analytics

# Install flutter bash completion
RUN mkdir ~/.bash-completion -p
RUN flutter bash-completion > ~/.bash-completion/flutter
RUN chmod +x ~/.bash-completion/flutter

# Source flutter bash completion
RUN echo 'source ~/.bash-completion/flutter' >> ~/.bashrc
