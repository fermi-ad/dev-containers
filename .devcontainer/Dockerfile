# This repository-local derivative keeps its tools out of the shared Python image.
# The readable release tag identifies the base; the index digest is authoritative.
FROM adregistry.fnal.gov/dev-containers/python:3.12-20261016-d9d7f4f@sha256:505b8c4e313b20e7b562c52ffae2b2d5a282fbea5fa0e8311eba619e3098bfcc

USER root
COPY setup.sh /tmp/devcontainer-setup.sh
RUN bash /tmp/devcontainer-setup.sh \
    && rm -f /tmp/devcontainer-setup.sh
USER dev
