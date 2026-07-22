# Dev Containers
This repo is the home of the source Dockerfiles for AD's prebuilt development containers. Software projects can create a `.devcontainer` directory with a `devcontainer.json` file inside, and VSCode will run its development environment out of the image specified in the JSON file. This eliminates "Works On My Machine" discrepancies. The `devcontainer.json` file should contain a line like `"image": "adregistry.fnal.gov/dev-containers/<container tag>"`.

## Structure
For each language, there should be a directory containing the Dockerfile that builds a minimal environment for developing with that language. There is also a GitHub Workflow for building an image from the selected Dockerfile and uploading to Harbor (adregistry.fnal.gov). 

## Generating new images in Harbor
If a new image is needed for development, make the required changes to the relevant Dockerfile and commit to `main`. 

Then, go to the **Actions** tab of this repo and select **Upload new image**:
1. Choose the language to build.
2. Enter the target language/tool version (e.g., `3.35.5`).

The workflow will automatically append the build date (or commit SHA) to form the full image tag (e.g., `3.35.5-20260722`), ensuring tag uniqueness regardless of git history changes.

## Adding a new container for a new language
If you'd like to add a container for a language that is not yet in this repo, create a directory with that language's name and add the relevant Dockerfile inside. **Be sure to add the language as an option in the `.github/workflows/build-new-container.yaml` file (needs to match the name of the directory you created!).**
