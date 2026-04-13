FROM ghcr.io/astral-sh/uv:python3.12-trixie

RUN apt-get update -y && apt-get install -y libgl1 sudo && apt-get clean -y

ENV UV_LINK_MODE="copy" UV_CACHE_DIR="/home/dev/.cache/uv" PIP_DISABLE_PIP_VERSION_CHECK="1" PYTHONDONTWRITEBYTECODE="1" PYTHONUNBUFFERED="1"

EXPOSE 8000

RUN useradd -ms /bin/bash -G sudo dev

USER dev

RUN echo "alias uv-sync='uv sync'" >> ~/.bashrc \
&& echo "alias test='uv run pytest'" >> ~/.bashrc \
&& echo "alias lint='uv run ruff check .'" >> ~/.bashrc \
&& echo "alias format='uv run ruff format .'" >> ~/.bashrc \
&& echo "alias run='uv run ap-python-starter-kit'" >> ~/.bashrc \
&& echo "alias rename-project='python3 scripts/rename_project.py'" >> ~/.bashrc \
&& echo "alias docs-serve='python -m http.server 8000 --directory docs'" >> ~/.bashrc
