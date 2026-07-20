#!/usr/bin/env bash
set -euo pipefail

CODEX_UID="${CODEX_UID:-1000}"
CODEX_GID="${CODEX_GID:-1000}"
CODEX_USER="${CODEX_USER:-codex}"
CODEX_HOME="${CODEX_HOME:-/home/codex}"

configure_docker_socket_access() {
  [[ -S /var/run/docker.sock ]] || return 0

  local docker_gid docker_group docker_group_entry
  docker_gid="$(stat -c '%g' /var/run/docker.sock)"

  if docker_group_entry="$(getent group "$docker_gid")"; then
    docker_group="${docker_group_entry%%:*}"
  else
    docker_group="docker-host"
    if getent group "$docker_group" >/dev/null; then
      docker_group="docker-host-$docker_gid"
    fi
    groupadd -g "$docker_gid" "$docker_group"
  fi

  usermod -aG "$docker_group" "$CODEX_USER"
}

if [[ "$(id -u)" == "0" ]]; then
  if ! getent group "$CODEX_GID" >/dev/null; then
    groupadd -g "$CODEX_GID" "$CODEX_USER"
  fi

  if ! id -u "$CODEX_USER" >/dev/null 2>&1; then
    useradd -m -u "$CODEX_UID" -g "$CODEX_GID" -s /bin/bash "$CODEX_USER"
  fi

  mkdir -p /workspace/repo "$CODEX_HOME" /cache
  chown "$CODEX_UID:$CODEX_GID" "$CODEX_HOME" /cache || true
  configure_docker_socket_access

  export HOME="$CODEX_HOME"
  exec gosu "$CODEX_USER" "$@"
fi

exec "$@"
