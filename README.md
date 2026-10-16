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
