"""Tests for plan_builds.py. Run with: python3 -m unittest discover -s .github/scripts"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import plan_builds as pb

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = pb.REGISTRY
SHA = "1a2b3c4" + "d" * 33
TODAY = "20261012"


def write_image(root: Path, name: str, dockerfile: str, config: dict | None) -> None:
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "Dockerfile").write_text(dockerfile)
    if config is not None:
        (directory / "image.json").write_text(json.dumps(config))


def fixture(root: Path) -> None:
    """base <- child (both arches), standalone (amd64 only)."""
    write_image(root, "base", "ARG BASE_VERSION=9.8\nFROM ubi:${BASE_VERSION}\n", {"version_arg": "BASE_VERSION"})
    write_image(
        root,
        "child",
        f"FROM {REGISTRY}/base\nARG CHILD_VERSION=1.2.3\nRUN install $CHILD_VERSION\n",
        {"version_arg": "CHILD_VERSION"},
    )
    write_image(
        root,
        "standalone",
        "ARG APP_VERSION=3.12\nFROM python:${APP_VERSION}\n",
        {"version_arg": "APP_VERSION", "platforms": ["amd64"]},
    )


def env(event: str, **extra: str) -> dict[str, str]:
    return {"EVENT_NAME": event, "SHA": SHA, **extra}


PUSH_MAIN = env("push", REF="refs/heads/main", BEFORE_SHA="f" * 40)
PULL_REQUEST = env("pull_request", REF="refs/pull/5/merge", BASE_SHA="e" * 40)


def names(entries: list[dict]) -> list[str]:
    return [e["image"] for e in entries]


class PlanTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def images(self) -> dict[str, pb.Image]:
        return pb.discover(self.root)

    def run_plan(self, environment: dict[str, str], changed_files: list[str] | None) -> dict:
        images = self.images()
        selected = pb.select(
            environment,
            images,
            changed=lambda base, head: changed_files,
            fork_point=lambda base, head: base,
        )
        return pb.plan(environment, images, selected, TODAY)


class DiscoverTests(PlanTestCase):
    def test_reads_version_platforms_and_parent(self) -> None:
        fixture(self.root)
        images = self.images()
        self.assertEqual(images["base"], pb.Image("base", "9.8", ("amd64", "arm64")))
        self.assertEqual(images["child"].version, "1.2.3")
        self.assertEqual(images["child"].parent, "base")
        self.assertEqual(images["child"].parent_ref, f"{REGISTRY}/base")
        self.assertEqual(images["standalone"].platforms, ("amd64",))

    def test_ignores_directories_without_dockerfile(self) -> None:
        fixture(self.root)
        (self.root / "docs").mkdir()
        (self.root / ".github").mkdir()
        (self.root / ".github" / "Dockerfile").write_text("FROM x\n")
        self.assertEqual(sorted(self.images()), ["base", "child", "standalone"])

    def assert_invalid(self, message: str) -> None:
        with self.assertRaisesRegex(pb.PlanError, message):
            self.images()

    def test_missing_image_json(self) -> None:
        write_image(self.root, "a", "ARG V=1\nFROM x\n", None)
        self.assert_invalid("missing image.json")

    def test_unknown_key(self) -> None:
        write_image(self.root, "a", "ARG V=1\nFROM x\n", {"version_arg": "V", "platform": ["amd64"]})
        self.assert_invalid("unknown image.json keys")

    def test_missing_version_arg_line(self) -> None:
        write_image(self.root, "a", "FROM x\n", {"version_arg": "V"})
        self.assert_invalid("exactly one 'ARG V=<version>'")

    def test_duplicate_version_arg_line(self) -> None:
        write_image(self.root, "a", "ARG V=1\nFROM x\nARG V=2\n", {"version_arg": "V"})
        self.assert_invalid("exactly one")

    def test_version_must_be_valid_tag(self) -> None:
        write_image(self.root, "a", "ARG V=1/2\nFROM x\n", {"version_arg": "V"})
        self.assert_invalid("not a valid tag")

    def test_invalid_platform(self) -> None:
        write_image(self.root, "a", "ARG V=1\nFROM x\n", {"version_arg": "V", "platforms": ["riscv"]})
        self.assert_invalid("platforms must be")

    def test_invalid_directory_name(self) -> None:
        write_image(self.root, "Bad_Name", "ARG V=1\nFROM x\n", {"version_arg": "V"})
        self.assert_invalid("not a valid image repository name")

    def test_unknown_in_repo_parent(self) -> None:
        write_image(self.root, "a", f"FROM {REGISTRY}/missing\nARG V=1\n", {"version_arg": "V"})
        self.assert_invalid("unknown in-repo image 'missing'")

    def test_parent_must_cover_child_platforms(self) -> None:
        write_image(self.root, "base", "ARG V=1\nFROM x\n", {"version_arg": "V", "platforms": ["amd64"]})
        write_image(self.root, "child", f"FROM {REGISTRY}/base\nARG V=1\n", {"version_arg": "V"})
        self.assert_invalid(r"needs \['arm64'\] but base")

    def test_only_one_level_of_in_repo_parents(self) -> None:
        fixture(self.root)
        write_image(self.root, "grandchild", f"FROM {REGISTRY}/child\nARG V=1\n", {"version_arg": "V"})
        self.assert_invalid("only be one level deep")


class SelectionTests(PlanTestCase):
    def setUp(self) -> None:
        super().setUp()
        fixture(self.root)

    def test_push_builds_changed_image_only(self) -> None:
        result = self.run_plan(PUSH_MAIN, ["standalone/Dockerfile", "README.md"])
        self.assertEqual(names(result["base"]), ["standalone"])
        self.assertEqual(result["dependent"], [])

    def test_changing_parent_rebuilds_children_in_second_tier(self) -> None:
        result = self.run_plan(PUSH_MAIN, ["base/Dockerfile"])
        self.assertEqual(names(result["base"]), ["base"])
        self.assertEqual(names(result["dependent"]), ["child"])

    def test_changing_child_does_not_rebuild_parent(self) -> None:
        result = self.run_plan(PUSH_MAIN, ["child/image.json"])
        self.assertEqual(result["base"], [])
        self.assertEqual(names(result["dependent"]), ["child"])

    def test_push_of_unrelated_files_builds_nothing(self) -> None:
        result = self.run_plan(PUSH_MAIN, ["README.md", ".github/workflows/build-image.yaml"])
        self.assertEqual(result["base"] + result["dependent"], [])

    def test_push_with_unknown_previous_commit_rebuilds_everything(self) -> None:
        result = self.run_plan(PUSH_MAIN, None)
        self.assertEqual(names(result["base"]) + names(result["dependent"]), ["base", "standalone", "child"])

    def test_pull_request_build_system_change_builds_everything(self) -> None:
        for path in pb.BUILD_SYSTEM_PATHS:
            with self.subTest(path=path):
                result = self.run_plan(PULL_REQUEST, [path])
                self.assertEqual(len(result["base"]) + len(result["dependent"]), 3)

    def test_dispatch_named_image_includes_children(self) -> None:
        result = self.run_plan(env("workflow_dispatch", REF="refs/heads/main", REQUESTED_IMAGE="base"), None)
        self.assertEqual(names(result["base"]), ["base"])
        self.assertEqual(names(result["dependent"]), ["child"])

    def test_dispatch_without_image_rebuilds_everything(self) -> None:
        result = self.run_plan(env("workflow_dispatch", REF="refs/heads/main", REQUESTED_IMAGE=" "), None)
        self.assertEqual(len(result["base"]) + len(result["dependent"]), 3)

    def test_dispatch_rejects_unknown_image(self) -> None:
        for requested in ("nope", "../base", "base/"):
            with self.subTest(requested=requested), self.assertRaisesRegex(pb.PlanError, "unknown image"):
                self.run_plan(env("workflow_dispatch", REQUESTED_IMAGE=requested), None)

    def test_unsupported_event(self) -> None:
        with self.assertRaisesRegex(pb.PlanError, "unsupported event"):
            self.run_plan(env("schedule"), [])


class TaggingTests(PlanTestCase):
    def setUp(self) -> None:
        super().setUp()
        fixture(self.root)

    def entry(self, result: dict, image: str) -> dict:
        return next(e for e in result["base"] + result["dependent"] if e["image"] == image)

    def test_main_push_gets_immutable_version_and_latest_tags(self) -> None:
        result = self.run_plan(PUSH_MAIN, ["standalone/Dockerfile"])
        self.assertTrue(result["push"])
        self.assertEqual(
            self.entry(result, "standalone")["tags"].splitlines(),
            [
                f"{REGISTRY}/standalone:3.12-{TODAY}-1a2b3c4",
                f"{REGISTRY}/standalone:3.12",
                f"{REGISTRY}/standalone:latest",
            ],
        )

    def test_dispatch_off_main_gets_only_immutable_tag(self) -> None:
        dispatch = env("workflow_dispatch", REF="refs/heads/feature", REQUESTED_IMAGE="standalone")
        result = self.run_plan(dispatch, None)
        self.assertTrue(result["push"])
        self.assertEqual(self.entry(result, "standalone")["tags"], f"{REGISTRY}/standalone:3.12-{TODAY}-1a2b3c4")

    def test_pull_request_never_pushes(self) -> None:
        result = self.run_plan(PULL_REQUEST, ["base/Dockerfile"])
        self.assertFalse(result["push"])
        self.assertEqual(len(self.entry(result, "base")["tags"].splitlines()), 1)

    def test_platforms_map_to_runners(self) -> None:
        result = self.run_plan(PUSH_MAIN, ["standalone/Dockerfile", "base/Dockerfile"])
        self.assertEqual(
            json.loads(self.entry(result, "standalone")["platforms"]),
            [{"platform": "amd64", "runner": "ubuntu-latest"}],
        )
        self.assertEqual(
            json.loads(self.entry(result, "base")["platforms"]),
            [{"platform": "amd64", "runner": "ubuntu-latest"}, {"platform": "arm64", "runner": "ubuntu-24.04-arm"}],
        )

    def test_child_is_pinned_to_parent_built_in_same_run(self) -> None:
        result = self.run_plan(PUSH_MAIN, ["base/Dockerfile"])
        self.assertEqual(
            self.entry(result, "child")["parent-context"],
            f"{REGISTRY}/base=docker-image://{REGISTRY}/base:9.8-{TODAY}-1a2b3c4",
        )

    def test_child_uses_registry_parent_when_parent_not_rebuilt(self) -> None:
        result = self.run_plan(PUSH_MAIN, ["child/Dockerfile"])
        self.assertEqual(self.entry(result, "child")["parent-context"], "")

    def test_pull_request_child_uses_registry_parent(self) -> None:
        # Nothing is pushed on PRs, so the just-built parent is not in the registry.
        result = self.run_plan(PULL_REQUEST, ["base/Dockerfile"])
        self.assertEqual(self.entry(result, "child")["parent-context"], "")


class GitTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = tmp.name
        self.git("init", "-q")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
            cwd=self.repo, check=True, capture_output=True, text=True,
        ).stdout.strip()

    def commit(self, path: str) -> str:
        file = Path(self.repo, path)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(path)
        self.git("add", path)
        self.git("commit", "-qm", path)
        return self.git("rev-parse", "HEAD")

    def changed(self, base: str, head: str) -> list[str] | None:
        cwd = Path.cwd()
        try:
            os.chdir(self.repo)
            return pb.git_changed_files(base, head)
        finally:
            os.chdir(cwd)

    def test_lists_files_between_commits(self) -> None:
        first = self.commit("a/Dockerfile")
        second = self.commit("b/Dockerfile")
        self.assertEqual(self.changed(first, second), ["b/Dockerfile"])

    def test_new_branch_and_rewritten_history_return_none(self) -> None:
        head = self.commit("a/Dockerfile")
        self.assertIsNone(self.changed(pb.NULL_SHA, head))
        self.assertIsNone(self.changed("", head))
        self.assertIsNone(self.changed("0123456789" * 4, head))


class RepositoryTests(unittest.TestCase):
    """Checks the real image directories in this repository."""

    def test_every_image_is_valid(self) -> None:
        images = pb.discover(REPO_ROOT)
        self.assertTrue(images)

    def test_xpra_base_stays_amd64_only(self) -> None:
        self.assertEqual(pb.discover(REPO_ROOT)["ap-python-xpra-base"].platforms, ("amd64",))


if __name__ == "__main__":
    unittest.main()
