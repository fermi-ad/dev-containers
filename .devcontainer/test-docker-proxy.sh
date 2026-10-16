#!/usr/bin/env bash
set -euo pipefail

script="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/start-docker-proxy.sh"
tmp_dir=$(mktemp -d)
daemon_pid=
cleanup() {
  if [[ -n "$daemon_pid" ]]; then
    kill "$daemon_pid" 2>/dev/null || true
    wait "$daemon_pid" 2>/dev/null || true
  fi
  for pid_path in "$tmp_dir/proxy/docker-proxy.pid" "$tmp_dir/failed-proxy/docker-proxy.pid"; do
    if [[ -f "$pid_path" ]]; then
      proxy_pid=$(sudo -n cat "$pid_path" 2>/dev/null || true)
      if [[ "$proxy_pid" =~ ^[0-9]+$ ]]; then
        sudo -n kill "$proxy_pid" 2>/dev/null || true
      fi
    fi
  done
  sudo -n rm -rf "$tmp_dir" || true
}
trap cleanup EXIT
chmod 0755 "$tmp_dir"

# The healthy fake daemon answers the Docker Engine API over a disposable Unix
# socket. The hung fake daemon accepts connections without answering. Neither
# test connects to the developer's real Docker daemon.
proxy_dir="$tmp_dir/proxy"
proxy_socket="$proxy_dir/docker.sock"
pid_file="$proxy_dir/docker-proxy.pid"
responsive_socket="$tmp_dir/responsive.sock"
python3 - "$responsive_socket" <<'PY' &
import json
import socket
import sys

server = socket.socket(socket.AF_UNIX)
server.bind(sys.argv[1])
server.listen()
version = json.dumps(
    {
        "Version": "test",
        "ApiVersion": "1.52",
        "MinAPIVersion": "1.24",
        "GitCommit": "test",
        "GoVersion": "go1.24",
        "Os": "linux",
        "Arch": "amd64",
        "KernelVersion": "test",
        "BuildTime": "test",
    }
).encode()
while True:
    connection, _ = server.accept()
    try:
        request = connection.recv(4096)
        path = request.split(b" ", 2)[1]
        body = b"OK" if path.endswith(b"/_ping") else version
        response = (
            b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
            + str(len(body)).encode()
            + b"\r\nConnection: close\r\n\r\n"
            + body
        )
        connection.sendall(response)
    finally:
        connection.close()
PY
daemon_pid=$!

for _ in {1..40}; do
  [[ -S "$responsive_socket" ]] && break
  sleep 0.05
done
if [[ ! -S "$responsive_socket" ]]; then
  printf 'Test daemon failed to create its Unix socket.\n' >&2
  exit 1
fi
chmod 0666 "$responsive_socket"

# Repeated lifecycle startup must reuse the same live proxy, and the real
# Docker CLI must complete its version request through the proxy.
sudo -n env \
  DEVCONTAINER_HOST_SOCKET="$responsive_socket" \
  DEVCONTAINER_PROXY_DIR="$proxy_dir" \
  DEVCONTAINER_PROXY_LOG="$tmp_dir/healthy-proxy.log" \
  DEVCONTAINER_PROBE_TIMEOUT=1 \
  DEVCONTAINER_STARTUP_TIMEOUT=3 \
  bash "$script"
first_pid=$(sudo -n cat "$pid_file")
sudo -n env \
  DEVCONTAINER_HOST_SOCKET="$responsive_socket" \
  DEVCONTAINER_PROXY_DIR="$proxy_dir" \
  DEVCONTAINER_PROXY_LOG="$tmp_dir/healthy-proxy.log" \
  DEVCONTAINER_PROBE_TIMEOUT=1 \
  DEVCONTAINER_STARTUP_TIMEOUT=3 \
  bash "$script"
second_pid=$(sudo -n cat "$pid_file")
if [[ "$first_pid" != "$second_pid" ]]; then
  printf 'Repeated startup replaced the working Docker proxy (%s -> %s).\n' \
    "$first_pid" "$second_pid" >&2
  exit 1
fi
if [[ ! -S "$proxy_socket" ]] || ! sudo -n kill -0 "$first_pid" 2>/dev/null; then
  printf 'Expected one live proxy after repeated startup.\n' >&2
  exit 1
fi
if [[ "$(sudo -n stat -c '%a:%U' "$proxy_socket")" != '600:dev' ]]; then
  printf 'Proxy socket must be mode 0600 and owned by dev.\n' >&2
  exit 1
fi

kill "$daemon_pid" 2>/dev/null || true
wait "$daemon_pid" 2>/dev/null || true
daemon_pid=
unresponsive_socket="$tmp_dir/unresponsive.sock"
failed_proxy_dir="$tmp_dir/failed-proxy"

python3 - "$unresponsive_socket" <<'PY' &
import socket
import sys
import time

server = socket.socket(socket.AF_UNIX)
server.bind(sys.argv[1])
server.listen()
connections = []
while True:
    connection, _ = server.accept()
    connections.append(connection)  # Deliberately never send a response.
    time.sleep(0.01)
PY
daemon_pid=$!

for _ in {1..40}; do
  [[ -S "$unresponsive_socket" ]] && break
  sleep 0.05
done
if [[ ! -S "$unresponsive_socket" ]]; then
  printf 'Unresponsive test daemon failed to create its Unix socket.\n' >&2
  exit 1
fi
chmod 0666 "$unresponsive_socket"

start_time=$SECONDS
set +e
output=$(sudo -n env \
  DEVCONTAINER_HOST_SOCKET="$unresponsive_socket" \
  DEVCONTAINER_PROXY_DIR="$failed_proxy_dir" \
  DEVCONTAINER_PROXY_LOG="$tmp_dir/failed-proxy.log" \
  DEVCONTAINER_PROBE_TIMEOUT=1 \
  DEVCONTAINER_STARTUP_TIMEOUT=3 \
  bash "$script" 2>&1)
status=$?
set -e
elapsed=$((SECONDS - start_time))

if [[ "$status" -eq 0 ]]; then
  printf 'Proxy startup unexpectedly succeeded against an unresponsive daemon.\n' >&2
  exit 1
fi
if [[ "$output" != *'within 3s'* || "$output" != *'Ensure the development Docker daemon is running'* ]]; then
  printf 'Startup failure did not provide actionable guidance:\n%s\n' "$output" >&2
  exit 1
fi
if [[ "$elapsed" -gt 8 ]]; then
  printf 'Unresponsive-daemon startup took %ss; expected a bounded failure.\n' "$elapsed" >&2
  exit 1
fi
if [[ -e "$failed_proxy_dir/docker.sock" || -e "$failed_proxy_dir/docker-proxy.pid" ]]; then
  printf 'Failed proxy startup left its socket or PID file behind.\n' >&2
  exit 1
fi

printf 'Docker proxy tests passed: real CLI reuses one proxy; unresponsive daemon fails in %ss and cleans up.\n' \
  "$elapsed"
