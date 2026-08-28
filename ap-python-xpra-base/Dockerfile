# AlmaLinux base for consistency with ACSys/Xpra images.

# ============================================================================
# Build arguments for version management
# Override at build time with: docker build --build-arg PYTHON_VERSION=3.13
# ============================================================================
ARG ALMALINUX_VERSION=9-base
ARG PYTHON_VERSION=3.12

# ============================================================================
# Base stage: Minimal runtime dependencies
# Shared by all deployment variants (CLI, GUI, Xpra)
# ============================================================================
FROM almalinux/${ALMALINUX_VERSION} AS base

# Re-declare args for use in this stage
ARG PYTHON_VERSION

USER root

# Install system dependencies and create non-root user
# Combined into single layer to reduce image size
RUN dnf install -y \
      krb5-libs \
      krb5-workstation \
      shadow-utils \
      python${PYTHON_VERSION} \
      python${PYTHON_VERSION}-devel \
      python3-tkinter \
      git \
      ca-certificates \
 && dnf clean all \
 && groupadd -g 1000 pygroup \
 && useradd -m -u 1000 -g pygroup pyuser

COPY --chmod=644 .kerberos/krb5.conf /etc/krb5.conf

# ============================================================================
# Xpra-base stage: Adds Xpra server for web-based GUI access
# Base for xpra-runtime deployment with HTML5 client
# ============================================================================
FROM base AS xpra-base

USER root

# Enable EPEL and Xpra repositories, then install Xpra server
# Install curl for start.sh readiness checks and healthchecks
# Install GUI runtime libraries (python already present from `base`)
# Install D-Bus and configure machine ID for Xpra
# Create runtime directories for Xpra with proper permissions
# User already created in `base` stage

RUN dnf install -y \
      'dnf-command(config-manager)' \
 && dnf config-manager --set-enabled crb \
 && dnf install -y epel-release \
 && curl -L -o /etc/yum.repos.d/xpra.repo \
      https://raw.githubusercontent.com/Xpra-org/xpra/master/packaging/repos/almalinux/xpra.repo \
 && dnf makecache \
 && dnf install -y \
      xpra-6.4.4* \
	  xpra-audio-6.4.4* \
	  xpra-client-6.4.4* \
	  xpra-client-gtk3-6.4.4* \
	  xpra-codecs-6.4.4* \
	  xpra-codecs-nvidia-6.4.4* \
	  xpra-common-6.4.4* \
	  xpra-filesystem-6.4.4* \
	  xpra-html5 \
	  xpra-server-6.4.4* \
	  xpra-x11-6.4.4* \
 && dnf install -y --allowerasing curl \
 && dnf install -y \
      dbus \
      libxcb \
      libxkbcommon \
      libxkbcommon-x11 \
      xcb-util \
      xcb-util-image \
      xcb-util-keysyms \
      xcb-util-renderutil \
      xcb-util-wm \
      xcb-util-cursor \
 && dnf clean all \
 && rm -f /etc/machine-id \
 && dbus-uuidgen --ensure=/etc/machine-id \
 && mkdir -p /run/user/1000 /tmp/runtime-pyuser /tmp/.X11-unix /run/xpra \
 && chown -R pyuser:pygroup /run/user/1000 /tmp/runtime-pyuser /run/xpra \
 && chmod 700 /run/user/1000 /tmp/runtime-pyuser /run/xpra \
 && chmod 1777 /tmp/.X11-unix
