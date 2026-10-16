#!/usr/bin/env bash
set -euo pipefail

# Run as root from postStartCommand. Expose the mounted host Docker socket
# through a dev-owned socket without changing the host socket's permissions.
host_socket=/var/run/docker-host.sock
proxy_dir=/run/devcontainer
proxy_socket="$proxy_dir/docker.sock"
pid_file="$proxy_dir/docker-proxy.pid"
log_file=/tmp/devcontainer-docker-proxy.log
docker_host=(docker --host "unix://$proxy_socket")

if [[ ! -S "$host_socket" ]]; then
  printf 'Host Docker socket not found at %s. Ensure Docker is running and reopen the container.\n' \
    "$host_socket" >&2
  exit 1
fi

if [[ -S "$proxy_socket" ]] && "${docker_host[@]}" version --format '{{.Server.Version}}' >/dev/null 2>&1; then
  exit 0
fi

install -d -m 0755 "$proxy_dir"
if [[ -f "$pid_file" ]]; then
  old_pid=$(<"$pid_file")
  if [[ "$old_pid" =~ ^[0-9]+$ ]] && kill -0 "$old_pid" 2>/dev/null; then
    old_command=$(tr '\0' ' ' <"/proc/$old_pid/cmdline" 2>/dev/null || true)
    if [[ "$old_command" == *socat*"$proxy_socket"* ]]; then
      kill "$old_pid"
    fi
  fi
fi
rm -f "$proxy_socket" "$pid_file"

# The local socket is mode 0600 and owned by dev. Forwarding still grants full
# control of the host daemon; this proxy only avoids changing host permissions.
nohup socat \
  "UNIX-LISTEN:$proxy_socket,fork,mode=0600,user=dev" \
  "UNIX-CONNECT:$host_socket" \
  >>"$log_file" 2>&1 </dev/null &
proxy_pid=$!
printf '%s\n' "$proxy_pid" >"$pid_file"

for _ in {1..40}; do
  if [[ -S "$proxy_socket" ]] && "${docker_host[@]}" version --format '{{.Server.Version}}' >/dev/null 2>&1; then
    exit 0
  fi
  sleep 0.25
done

kill "$proxy_pid" 2>/dev/null || true
printf 'Could not connect to the host Docker daemon through %s. See %s.\n' \
  "$proxy_socket" "$log_file" >&2
exit 1
