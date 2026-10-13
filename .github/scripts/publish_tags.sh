#!/usr/bin/env bash
# Applies an image's final tags by pointing them at its per-platform images
# (<immutable tag>-<platform>, pushed by the build job). Every published image is
# tagged by this script: multi-arch images in the publish job once all platforms
# are built, single-platform images at the end of their only build job.
#
# Environment:
#   IMAGE      image directory name (for the step summary)
#   TAGS       newline-separated fully-qualified tags; the first is the immutable tag
#   PLATFORMS  JSON list of {"platform": ...} objects
set -euo pipefail

immutable=$(head -n1 <<< "$TAGS")
args=()
while IFS= read -r tag; do
  [ -n "$tag" ] && args+=(--tag "$tag")
done <<< "$TAGS"
for platform in $(jq -r '.[].platform' <<< "$PLATFORMS"); do
  args+=("${immutable}-${platform}")
done
docker buildx imagetools create "${args[@]}"

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  {
    echo "### ${IMAGE}"
    echo '```'
    echo "$TAGS"
    echo '```'
  } >> "$GITHUB_STEP_SUMMARY"
fi
