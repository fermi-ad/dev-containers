#!/usr/bin/env bash
set -euo pipefail

# Install development-only tools in this container, not in the shared image.
# Docker commands will use a root-started, container-local proxy for the
# host socket. The proxy changes socket permissions only inside this container.

if [[ "$(id -u)" -eq 0 ]]; then
  sudo=()
else
  sudo=(sudo -n)
fi

# curl, gpg, sha256sum, and tar are already present in the base image.
"${sudo[@]}" microdnf --setopt=install_weak_deps=0 install -y \
  jq-1.6-19.el9_8.2 \
  socat-1.7.4.1-8.el9

# Configure Docker's official CentOS 9 repository for the signed RHEL 9 CLI
# and Buildx packages. Verify the upstream signing-key fingerprint before
# trusting packages from this repository.
tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT
curl -fsSL https://download.docker.com/linux/centos/gpg -o "$tmp_dir/docker.gpg"
fingerprint=$(gpg --batch --show-keys --with-colons "$tmp_dir/docker.gpg" | awk -F: '$1 == "fpr" { print $10; exit }')
expected_fingerprint=060A61C51B558A7F742B77AAC52FEB6B621E9F35
if [[ "$fingerprint" != "$expected_fingerprint" ]]; then
  printf 'Unexpected Docker repository signing-key fingerprint: %s\n' "$fingerprint" >&2
  exit 1
fi
"${sudo[@]}" install -m 0644 "$tmp_dir/docker.gpg" /etc/pki/rpm-gpg/RPM-GPG-KEY-docker
"${sudo[@]}" tee /etc/yum.repos.d/docker-ce.repo >/dev/null <<'REPO'
[docker-ce-stable]
name=Docker CE Stable - $basearch
baseurl=https://download.docker.com/linux/centos/9/$basearch/stable
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-docker
REPO

# Keep CLI and Buildx at verified versions. jq and socat come from the
# repositories configured by the UBI base image.
"${sudo[@]}" microdnf --setopt=install_weak_deps=0 install -y \
  docker-ce-cli-29.9.1-1.el9 \
  docker-buildx-plugin-0.38.0-1.el9
"${sudo[@]}" microdnf clean all

# Install a pinned ShellCheck release. Upstream does not publish checksum
# files, so pin the release artifact hashes here for each supported arch.
case "$(uname -m)" in
  x86_64)
    shellcheck_arch=x86_64
    shellcheck_sha256=b7af85e41cc99489dcc21d66c6d5f3685138f06d34651e6d34b42ec6d54fe6f6
    ;;
  aarch64)
    shellcheck_arch=aarch64
    shellcheck_sha256=68a8133197a50beb8803f8d42f9908d1af1c5540d4bb05fdfca8c1fa47decefc
    ;;
  *)
    printf 'Unsupported architecture for ShellCheck: %s\n' "$(uname -m)" >&2
    exit 1
    ;;
esac
shellcheck_archive="shellcheck-v0.11.0.linux.${shellcheck_arch}.tar.gz"
curl -fsSL "https://github.com/koalaman/shellcheck/releases/download/v0.11.0/${shellcheck_archive}" \
  -o "$tmp_dir/$shellcheck_archive"
printf '%s  %s\n' "$shellcheck_sha256" "$tmp_dir/$shellcheck_archive" | sha256sum --check
mkdir "$tmp_dir/shellcheck"
tar -xzf "$tmp_dir/$shellcheck_archive" -C "$tmp_dir/shellcheck"
"${sudo[@]}" install -m 0755 \
  "$tmp_dir/shellcheck/shellcheck-v0.11.0/shellcheck" \
  /usr/local/bin/shellcheck
"${sudo[@]}" install -D -m 0644 \
  "$tmp_dir/shellcheck/shellcheck-v0.11.0/LICENSE.txt" \
  /usr/share/licenses/shellcheck/LICENSE.txt

printf '\nInstalled development tools:\n'
jq --version
docker --version
docker buildx version
shellcheck --version | head -n 2
