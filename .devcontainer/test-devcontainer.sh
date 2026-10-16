#!/usr/bin/env bash
set -euo pipefail

# Run from the repository root, inside the devcontainer. These are deliberately
# the same commands listed in the README's Checks section.
python3 -m unittest discover -s .github/scripts -v
shellcheck .github/scripts/*.sh
shellcheck .devcontainer/*.sh
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.12
if git grep -nIP '\t|[ \t]+$' -- .; then
  printf 'Tabs or trailing whitespace found.\n' >&2
  exit 1
else
  grep_status=$?
  if [[ "$grep_status" -ne 1 ]]; then
    exit "$grep_status"
  fi
fi
