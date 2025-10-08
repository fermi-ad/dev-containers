# Dev Containers
This repo is the home of the source Dockerfiles for AD's prebuilt development containers. Software projects can create a `.devcontainer` directory with a `devcontainer.json` file inside, and VSCode will run its development environment out of the image specified in the JSON file. This eliminates "Works On My Machine" discrepancies. The `devcontainer.json` file should contain a line like `"image": "adregistry.fnal.gov/dev-containers/<container tag>"`.

### Structure
For each language, there should be a directory containing the Dockerfile that builds a minimal environment for developing with that language. There is also a GitHub Workflow for building an image from the selected Dockerfile and uploading to Harbor (adregistry.fnal.gov). 

### Generating new images in Harbor
If a new image is needed for development, make the required changes (if any) to the relevant Dockerfile and commit to `main`. Then, go to the Actions tab of this repo and select the "Upload new image" option from the left menu. A "Run workflow" button should appear on the right - click the dropdown and choose the language you want to build for. Type the language version into the text field. If the new image is adding other dependencies and not changing language version, add a descriptor after the version to disambiguate the image from previous versions. (e.g., adding the `wget` command to the image of Flutter 3.35.5, enter "3.35.5-wget" as the version)

### Adding a new container for a new language
If you'd like to add a container for a language that is not yet in this repo, create a directory with that language's name and add the relevant Dockerfile inside. **Be sure to add the language as an option in the `.github/workflows/build-new-container.yaml` file (needs to match the name of the directory you created!).**
