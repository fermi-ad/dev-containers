# Dev Containers
This repo is the home of the source Dockerfiles for AD's prebuilt development containers. Software projects can create a `.devcontainer` directory with a `devcontainer.json` file inside, and VSCode will run its development environment out of the image specified in the JSON file. This eliminates "Works On My Machine" discrepancies. The `devcontainer.json` file should contain a line like `"image": "adregistry.fnal.gov/dev-containers/<image>:<tag>"`.

## Structure
Each top-level directory is one image, published to Harbor as `adregistry.fnal.gov/dev-containers/<directory>`. A directory contains:

- `Dockerfile`: builds the image.
- `image.json`: build settings for the image:

  ```json
  {
    "version_arg": "FLUTTER_VERSION",
    "platforms": ["amd64", "arm64"]
  }
  ```

  - `version_arg` (required): the Dockerfile `ARG` that sets the image's version. The Dockerfile must declare it exactly once with a default value (`ARG FLUTTER_VERSION=3.47.7`), and that `ARG` should drive what gets installed. Because the same value is used for both the tag and the install, the tag always matches what is in the image.
  - `platforms` (optional): any of `amd64` and `arm64`. Defaults to both. `ap-python-xpra-base` is `amd64` only because Xpra does not work reliably on arm64.

An image can build `FROM adregistry.fnal.gov/dev-containers/<other image>`, as most images here do with `redhat-ubi9-minimal`. These relationships are detected automatically: when the base image is rebuilt, every image built from it is rebuilt afterwards against the new base.

## Python image
The `python` image installs uv-managed Python. The default `python3` and `python` commands, as well as the versioned executable, use the release selected by `PYTHON_VERSION`. These commands are available on `PATH` for the image's `dev` user; no separate system Python is installed.

## This repository's dev container

Open this repository in VS Code with the Dev Containers extension, then run **Dev Containers: Reopen in Container**. The container uses this repository's Python image pinned to an immutable tag; `.devcontainer/setup.sh` installs repository-only tools such as `jq`, ShellCheck, Docker CLI, and Buildx. These tools are intentionally not added to the shared Python image. After setup, run `bash .devcontainer/test-devcontainer.sh` from the integrated terminal as the `dev` user to run every command in [Checks](#checks).

The dev container uses **Docker outside of Docker**: its Docker CLI connects through a container-local proxy to the Docker daemon on the host. Builds reuse the host's Docker cache and images; there is no second daemon. The dev container is not privileged. **Docker-in-Docker** would give this devcontainer its own daemon, storage, and cache and can mount files that exist only inside it, but needs a separate daemon setup and the standard feature runs privileged; that is not a security sandbox. A **dedicated remote daemon/VM** can provide a stronger boundary for untrusted workloads, at the cost of extra infrastructure, network setup, and a remote build cache. Omitting Docker access would also mean the README's Docker-based actionlint check cannot run unchanged.

> **Security:** Access to a rootful Docker socket grants the ability to control that host's Docker daemon and is effectively root-equivalent on the daemon host. Treat code and tools run in this dev container as trusted with that authority. Commands such as `docker system prune` can affect other work on the host. The proxy limits socket permissions inside the dev container but does **not** limit Docker API authority. No host socket permissions are changed.

The socket setup expects a local Linux Docker Engine **19.03 or newer** (Engine API 1.40+) at `/var/run/docker.sock` and a workspace backed by a host filesystem path, mounted at the same absolute path inside the dev container. Docker Desktop, rootless Docker, remote Docker contexts, Windows hosts, and workspaces cloned into a container volume may need different socket or path configuration; they are not currently covered by the checked setup. Registry credentials are not copied into the dev container; authenticate separately only if you need to pull private images. See Docker's [Engine API version matrix](https://docs.docker.com/reference/api/engine/version-history/) for the client/server compatibility reference.

The Docker CLI and Buildx versions, ShellCheck release and checksums, and Docker repository signing-key fingerprint are pinned in `.devcontainer/setup.sh`. When updating them, verify the upstream release and checksum/signing key, update the script, rebuild the dev container, and rerun every command in [Checks](#checks). The Python base image should be updated only to an immutable tag that exists in Harbor and supports both `amd64` and `arm64`.

## Building images
The [Build images](.github/workflows/build-images.yaml) workflow decides what to build from the files that changed:

| Event | What builds | Published to Harbor? |
| --- | --- | --- |
| Pull request | Images whose directories changed, plus images built from them. Changing the workflow builds everything. | No, the build only checks that the images still build |
| Push to `main` | Images whose directories changed, plus images built from them | Yes |
| Manual run (**Actions → Build images → Run workflow**) | The image you name, plus images built from it; leave the name blank to rebuild everything | Yes |

To release a change to an image, change its directory and merge to `main`. Use a manual run to pick up base-image or package updates when no files have changed.

## Tags
Each published image gets the following tags:

| Tag | Example | Changes? |
| --- | --- | --- |
| `<version>-<date>-<sha>` | `3.47.7-20261012-1a2b3c4` | Never. Pin to this for reproducible environments. |
| `<version>` | `3.47.7` | Moves to the newest build of that version |
| `latest` | `latest` | Moves to the newest build |

`<version>` is the default of the image's `version_arg`, `<date>` is the UTC build date, and `<sha>` is the short commit hash. Only builds of `main` move `<version>` and `latest`; a manual run on any other branch publishes only the immutable tag.

To release a new tool version, update the `ARG` default in the Dockerfile. To change something else, such as adding a package, just change the Dockerfile; the new build gets a new immutable tag under the same version.

## Adding a new image
Create a directory named after the image containing a `Dockerfile` and an `image.json`. The workflow picks the new directory up automatically, so no workflow changes are needed. Open a pull request to check that it builds, then merge to publish it.

## Checks
Before any image builds, the workflow's `checks` job runs the following. You can run the same checks locally:

```sh
python3 -m unittest discover -s .github/scripts -v   # build planner tests, including validation of every image.json
shellcheck .github/scripts/*.sh   # script lint
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.12   # workflow lint
git grep -nIP '\t|[ \t]+$' -- .   # must print nothing: no tabs or trailing whitespace
```
