#!/usr/bin/env python3
"""Decide which dev-container images a workflow run builds, and how to tag them.

An image is any top-level directory containing a Dockerfile and an image.json:

    {
      "version_arg": "FLUTTER_VERSION",   # Dockerfile ARG whose default is the image version
      "platforms": ["amd64", "arm64"]     # optional; defaults to both
    }

Images built FROM another image in this repo (FROM adregistry.fnal.gov/dev-containers/<name>)
are "dependent" and build after the "base" tier. Rebuilding a parent rebuilds its children,
and on publishing runs the children are built against the parent image just pushed.

Reads its inputs from environment variables set by .github/workflows/build-images.yaml and
writes `base`, `dependent` and `push` to $GITHUB_OUTPUT (or only stdout when run locally).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REGISTRY = "adregistry.fnal.gov/dev-containers"
RUNNERS = {"amd64": "ubuntu-latest", "arm64": "ubuntu-24.04-arm"}
DEFAULT_PLATFORMS = ["amd64", "arm64"]
# On pull requests, changes to these rebuild (but never publish) every image.
BUILD_SYSTEM_PATHS = (
    ".github/workflows/build-images.yaml",
    ".github/workflows/build-image.yaml",
    ".github/scripts/plan_builds.py",
)
NULL_SHA = "0" * 40
NAME_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
TAG_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")
# Captures the full in-repo reference as written, and the image name within it.
PARENT_RE = re.compile(
    r"^\s*FROM\s+(?:--platform=\S+\s+)?(" + re.escape(REGISTRY) + r"/([^\s:@]+)\S*)",
    re.IGNORECASE | re.MULTILINE,
)


class PlanError(Exception):
    pass


@dataclass(frozen=True)
class Image:
    name: str
    version: str
    platforms: tuple[str, ...]
    parent: str | None = None
    parent_ref: str | None = None  # the FROM reference exactly as written


def load_image(directory: Path) -> Image:
    name = directory.name
    if not NAME_RE.match(name):
        raise PlanError(f"{name}: directory name is not a valid image repository name")

    config_path = directory / "image.json"
    if not config_path.is_file():
        raise PlanError(f"{name}: missing image.json")
    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError as err:
        raise PlanError(f"{name}: invalid image.json: {err}") from err
    if not isinstance(config, dict):
        raise PlanError(f"{name}: image.json must be an object")

    unknown = set(config) - {"version_arg", "platforms"}
    if unknown:
        raise PlanError(f"{name}: unknown image.json keys: {sorted(unknown)}")

    platforms = config.get("platforms", DEFAULT_PLATFORMS)
    if (
        not isinstance(platforms, list)
        or not platforms
        or len(set(platforms)) != len(platforms)
        or any(p not in RUNNERS for p in platforms)
    ):
        raise PlanError(f"{name}: platforms must be a non-empty subset of {sorted(RUNNERS)}")

    version_arg = config.get("version_arg")
    if not isinstance(version_arg, str) or not version_arg:
        raise PlanError(f"{name}: image.json must set version_arg")

    dockerfile = (directory / "Dockerfile").read_text()
    matches = re.findall(
        rf"^\s*ARG\s+{re.escape(version_arg)}=(\S+)\s*$", dockerfile, re.MULTILINE
    )
    if len(matches) != 1:
        raise PlanError(
            f"{name}: Dockerfile needs exactly one 'ARG {version_arg}=<version>' line"
        )
    version = matches[0].strip("\"'")
    if not TAG_RE.match(version):
        raise PlanError(f"{name}: {version_arg}={version!r} is not a valid tag")

    parents = PARENT_RE.findall(dockerfile)
    if len({ref for ref, _ in parents}) > 1:
        raise PlanError(f"{name}: builds FROM more than one in-repo image")
    parent_ref, parent = parents[0] if parents else (None, None)

    return Image(name, version, tuple(platforms), parent, parent_ref)


def discover(root: Path) -> dict[str, Image]:
    images = {
        d.name: load_image(d)
        for d in sorted(root.iterdir())
        if d.is_dir() and not d.name.startswith(".") and (d / "Dockerfile").is_file()
    }
    for image in images.values():
        if image.parent is None:
            continue
        parent = images.get(image.parent)
        if parent is None:
            raise PlanError(f"{image.name}: FROM unknown in-repo image {image.parent!r}")
        if parent.parent is not None:
            raise PlanError(
                f"{image.name}: in-repo base images may only be one level deep "
                f"({image.name} -> {parent.name} -> {parent.parent})"
            )
        missing = set(image.platforms) - set(parent.platforms)
        if missing:
            raise PlanError(
                f"{image.name}: needs {sorted(missing)} but {parent.name} is not built for it"
            )
    return images


def images_in(changed_files: list[str], images: dict[str, Image]) -> set[str]:
    return {f.split("/", 1)[0] for f in changed_files if "/" in f} & set(images)


def with_dependents(selected: set[str], images: dict[str, Image]) -> set[str]:
    return selected | {i.name for i in images.values() if i.parent in selected}


def git_changed_files(base: str, head: str) -> list[str] | None:
    """Files changed between base and head, or None when base is unusable."""
    if not base or base == NULL_SHA:
        return None
    exists = subprocess.run(["git", "cat-file", "-e", f"{base}^{{commit}}"], capture_output=True)
    if exists.returncode != 0:  # e.g. a force push rewrote history
        return None
    out = subprocess.run(
        ["git", "diff", "--name-only", base, head], check=True, capture_output=True, text=True
    ).stdout
    return out.splitlines()


def merge_base(a: str, b: str) -> str:
    return subprocess.run(
        ["git", "merge-base", a, b], check=True, capture_output=True, text=True
    ).stdout.strip()


def select(
    env: dict[str, str],
    images: dict[str, Image],
    changed=git_changed_files,
    fork_point=merge_base,
) -> set[str]:
    event = env["EVENT_NAME"]
    if event == "workflow_dispatch":
        requested = env.get("REQUESTED_IMAGE", "").strip()
        if not requested:
            return set(images)
        if requested not in images:
            raise PlanError(f"unknown image {requested!r}; choose from {sorted(images)}")
        return with_dependents({requested}, images)

    if event == "pull_request":
        files = changed(fork_point(env["BASE_SHA"], env["SHA"]), env["SHA"])
        if files is not None and any(f in BUILD_SYSTEM_PATHS for f in files):
            return set(images)
    elif event == "push":
        files = changed(env.get("BEFORE_SHA", ""), env["SHA"])
    else:
        raise PlanError(f"unsupported event {event!r}")

    if files is None:
        return set(images)
    return with_dependents(images_in(files, images), images)


def plan(env: dict[str, str], images: dict[str, Image], selected: set[str], today: str) -> dict:
    push = env["EVENT_NAME"] in ("push", "workflow_dispatch")
    on_main = env.get("REF") == "refs/heads/main"
    short_sha = env["SHA"][:7]

    def tags(image: Image) -> list[str]:
        repo = f"{REGISTRY}/{image.name}"
        result = [f"{repo}:{image.version}-{today}-{short_sha}"]  # immutable
        if push and on_main:
            result += [f"{repo}:{image.version}", f"{repo}:latest"]  # moving
        return result

    def entry(image: Image) -> dict:
        parent_context = ""
        # Pin children to the exact parent pushed earlier in this run, rather than
        # whatever the FROM reference resolves to in the registry.
        if push and image.parent in selected:
            parent_context = f"{image.parent_ref}=docker-image://{tags(images[image.parent])[0]}"
        return {
            "image": image.name,
            "version": image.version,
            "platforms": json.dumps(
                [{"platform": p, "runner": RUNNERS[p]} for p in image.platforms]
            ),
            "tags": "\n".join(tags(image)),
            "multi-arch": len(image.platforms) > 1,
            "parent-context": parent_context,
        }

    ordered = [images[n] for n in sorted(selected)]
    return {
        "base": [entry(i) for i in ordered if i.parent is None],
        "dependent": [entry(i) for i in ordered if i.parent is not None],
        "push": push,
    }


def main() -> int:
    env = dict(os.environ)
    try:
        images = discover(Path.cwd())
        selected = select(env, images)
        result = plan(env, images, selected, datetime.now(timezone.utc).strftime("%Y%m%d"))
    except PlanError as err:
        print(f"::error::{err}", file=sys.stderr)
        return 1

    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a") as fh:
            for key, value in result.items():
                fh.write(f"{key}={json.dumps(value)}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
