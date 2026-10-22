#!/usr/bin/env bash
set -euo pipefail

# Run as root from postStartCommand. Expose the mounted host Docker socket
# through a dev-owned socket without changing the host socket's permissions.
host_socket=${DEVCONTAINER_HOST_SOCKET:-/var/run/docker-host.sock}
proxy_dir=${DEVCONTAINER_PROXY_DIR:-/run/devcontainer}
proxy_socket="$proxy_dir/docker.sock"
pid_file="$proxy_dir/docker-proxy.pid"
log_file=${DEVCONTAINER_PROXY_LOG:-/tmp/devcontainer-docker-proxy.log}
probe_timeout=${DEVCONTAINER_PROBE_TIMEOUT:-2}
startup_timeout=${DEVCONTAINER_STARTUP_TIMEOUT:-15}
docker_bin=${DEVCONTAINER_DOCKER_BIN:-docker}
socat_bin=${DEVCONTAINER_SOCAT_BIN:-socat}
docker_host=("$docker_bin" --host "unix://$proxy_socket")
deadline=0

if [[ ! "$probe_timeout" =~ ^[1-9][0-9]*$ || ! "$startup_timeout" =~ ^[1-9][0-9]*$ ]]; then
  printf 'Docker proxy probe and startup timeouts must be positive integers.\n' >&2
  exit 2
fi

if [[ ! -S "$host_socket" ]]; then
  printf 'Host Docker socket not found at %s. Ensure Docker is running and reopen the container.\n' \
    "$host_socket" >&2
  exit 1
fi

# A root-started postStartCommand may leave root-owned state under /run.
# Grant dev ownership so later lifecycle invocations can acquire the lock.
install -d -m 0755 -o dev -g dev "$proxy_dir"
# Serialize concurrent lifecycle hooks so they reuse one working proxy.
# Keep the lock file writable by dev across root-run lifecycle invocations.
touch "$proxy_dir/start.lock"
chown dev:dev "$proxy_dir/start.lock"
deadline=$((SECONDS + startup_timeout))
exec 9<>"$proxy_dir/start.lock"
lock_timeout=$((deadline - SECONDS))
if (( lock_timeout <= 0 )) || ! flock --exclusive --wait "$lock_timeout" 9; then
  printf 'Timed out after %ss waiting for another Docker proxy startup to finish.\n' \
    "$startup_timeout" >&2
  exit 1
fi

probe_docker() {
  local remaining=$((deadline - SECONDS))
  (( remaining > 0 )) || return 1
  local probe_limit=$probe_timeout
  if (( remaining < probe_limit )); then
    probe_limit=$remaining
  fi
  timeout --signal=KILL "$probe_limit" \
    "${docker_host[@]}" version --format '{{.Server.Version}}' >/dev/null 2>&1
}

stop_proxy() {
  local pid=${1:-}
  [[ "$pid" =~ ^[0-9]+$ ]] || return 0
  # socat forks one child per accepted connection; close those too on failure.
  local children_file="/proc/$pid/task/$pid/children"
  if [[ -r "$children_file" ]]; then
    local children=()
    read -r -a children <"$children_file" || true
    for child in "${children[@]}"; do
      kill "$child" 2>/dev/null || true
    done
  fi
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}

# Reopening a healthy container should not create another proxy.
if [[ -S "$proxy_socket" ]] && probe_docker; then
  exit 0
fi

# Remove a stale proxy from a previous failed or interrupted startup.
if [[ -f "$pid_file" ]]; then
  old_pid=$(<"$pid_file")
  if [[ "$old_pid" =~ ^[0-9]+$ ]] && kill -0 "$old_pid" 2>/dev/null; then
    old_command=$(tr '\0' ' ' <"/proc/$old_pid/cmdline" 2>/dev/null || true)
    if [[ "$old_command" == *socat*"$proxy_socket"* ]]; then
      stop_proxy "$old_pid"
    fi
  fi
fi
rm -f "$proxy_socket" "$pid_file"

# The local socket is mode 0600 and owned by dev. Forwarding still grants full
# control of the host daemon; this proxy only avoids changing host permissions.
nohup "$socat_bin" \
  "UNIX-LISTEN:$proxy_socket,fork,mode=0600,user=dev" \
  "UNIX-CONNECT:$host_socket" \
  9>&- >>"$log_file" 2>&1 </dev/null &
proxy_pid=$!
proxy_ready=false
# The EXIT trap invokes this indirectly after a startup failure.
# ShellCheck versions differ on whether they detect trap-registered functions.
# shellcheck disable=SC2317,SC2329
cleanup_failed_start() {
  if [[ "$proxy_ready" != true ]]; then
    stop_proxy "$proxy_pid"
    rm -f "$proxy_socket" "$pid_file"
  fi
}
trap cleanup_failed_start EXIT
printf '%s\n' "$proxy_pid" >"$pid_file"

for _ in {1..40}; do
  if [[ -S "$proxy_socket" ]] && probe_docker; then
    proxy_ready=true
    exit 0
  fi
  if (( SECONDS >= deadline )); then
    break
  fi
  sleep 0.25
done

printf 'Could not reach the Docker daemon at %s through %s within %ss (each probe is limited to %ss). Ensure the development Docker daemon is running and reachable; proxy log: %s.\n' \
  "$host_socket" "$proxy_socket" "$startup_timeout" "$probe_timeout" "$log_file" >&2
exit 1
