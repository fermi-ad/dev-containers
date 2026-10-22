# Devcontainer image security note

This note records the available Harbor scan evidence and the project's maintenance approach. It is **not** a claim that the image has zero vulnerabilities, that every scanner finding applies, or that findings have received formal risk acceptance.

## Scan evidence

Harbor's NeuVector 4.245 scan of the Python base image's multi-platform index was generated **2026-10-16 14:46 UTC** for `adregistry.fnal.gov/dev-containers/python:3.12-20261016-d9d7f4f`, index digest `sha256:505b8c4e313b20e7b562c52ffae2b2d5a282fbea5fa0e8311eba619e3098bfcc` ([Harbor artifact](https://adregistry.fnal.gov/harbor/projects/dev-containers/repositories/python/artifacts-tab); [vulnerability report API](https://adregistry.fnal.gov/api/v2.0/projects/dev-containers/repositories/python/artifacts/sha256:505b8c4e313b20e7b562c52ffae2b2d5a282fbea5fa0e8311eba619e3098bfcc/additions/vulnerabilities)). The report contained 639 High-severity rows, including 415 `kernel-headers` rows. Rows repeat CVEs across packages and platforms, so the raw count is not a count of distinct exploitable vulnerabilities.

Excluding `kernel-headers`, the report contains 81 distinct High CVE identifiers across 13 package names. The report text explicitly says Red Hat's versions are **not affected** for 16 of those identifiers. The remaining findings are scanner matches in userspace packages; they have not been individually confirmed against vendor advisories here.

The scan covers the pinned Python base image, **not** the derived devcontainer or its added `jq`, `socat`, Docker CLI, Buildx, and ShellCheck. This PR does not establish a zero-vulnerability security status for the final image.

## Maintenance approach

The pinned Python image is the current intended base for this repository's devcontainer. Ideally, new and updated images would have zero reported vulnerabilities, but that is difficult to guarantee in practice. This devcontainer is part of the repository's container ecosystem and should be kept current when the base containers are routinely updated; its scan results should be reviewed as part of that maintenance.

The Docker socket makes the consequence of a compromised development tool higher, as explained in the [README](../README.md#this-repositorys-dev-container). This note records the scan and maintenance intent; it does not resolve every finding or constitute formal risk acceptance. PR reviewers can decide whether any specific finding needs a fix or a separate follow-up.
