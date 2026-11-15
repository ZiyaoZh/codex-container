#!/usr/bin/env bash
set -euo pipefail

CODEX_UID="${CODEX_UID:-1000}"
CODEX_GID="${CODEX_GID:-1000}"
CODEX_USER="${CODEX_USER:-user}"
CONTAINER_USER_HOME="${CONTAINER_USER_HOME:-/home/$CODEX_USER}"
export CODEX_HOME="${CODEX_HOME:-$CONTAINER_USER_HOME/.codex}"

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
    useradd -M -d "$CONTAINER_USER_HOME" -u "$CODEX_UID" -g "$CODEX_GID" -s /bin/bash "$CODEX_USER"
  fi

  if [[ "$(id -u "$CODEX_USER")" != "$CODEX_UID" || "$(id -g "$CODEX_USER")" != "$CODEX_GID" ]]; then
    echo "Container user $CODEX_USER does not match requested UID/GID" >&2
    exit 1
  fi
  usermod -d "$CONTAINER_USER_HOME" "$CODEX_USER"
  usermod -aG codex-sudo "$CODEX_USER"
  mkdir -p /workspace/repo "$CONTAINER_USER_HOME/.cache" /cache
  chown "$CODEX_UID:$CODEX_GID" "$CONTAINER_USER_HOME" "$CONTAINER_USER_HOME/.cache" /cache || true
  configure_docker_socket_access

  export HOME="$CONTAINER_USER_HOME"
  export USER="$CODEX_USER" LOGNAME="$CODEX_USER"
  exec gosu "$CODEX_USER" "$@"
fi

exec "$@"
