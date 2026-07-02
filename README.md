# Codex Container

Universal Docker environment for running Codex and Claude Code against any local repository.

The image contains:

- OpenAI Codex CLI: `codex`
- Anthropic Claude Code CLI: `claude`
- Common development tools: `git`, `git-lfs`, `ripgrep`, `fd`, `python3`, `pip`, `venv`, `build-essential`, `docker`, `jq`, `openssh-client`, and basic editors

The container does not bake in Codex or Claude credentials. Runtime configuration is mounted from the host.

## Build

Run this from any directory:

```bash
docker build -t codex-universal:latest /workspace/codex-container
```

Or from this directory:

```bash
docker build -t codex-universal:latest .
```

## Run Codex

In any repository:

```bash
cd /path/to/repo
/workspace/codex-container/codex-container
```

If the launcher is on your `PATH`:

```bash
cd /path/to/repo
codex-container
```

## Run Claude Code

```bash
cd /path/to/repo
/workspace/codex-container/codex-container --agent claude
```

If the launcher is on your `PATH`:

```bash
cd /path/to/repo
codex-container --agent claude
```

## Open A Shell

```bash
cd /path/to/repo
/workspace/codex-container/codex-container bash
```

## Install The Launcher

Optional, but convenient:

```bash
sudo ln -sf /workspace/codex-container/codex-container /usr/local/bin/codex-container
```

Then use:

```bash
cd /path/to/repo
codex-container
codex-container --agent claude
codex-container bash
```

## Runtime Layout

The current repository is mounted here:

```text
/workspace/repo
```

The container runs with this working directory:

```text
/workspace/repo
```

The container home is mounted here:

```text
/home/codex
```

By default, the host path for the persistent container home is:

```text
~/.cache/codex-container/home
```

This keeps agent state across `--rm` container runs.

## Default Mounts

The launcher mounts these host paths when available:

```text
current repo                         -> /workspace/repo
~/.cache/codex-container/home         -> /home/codex
~/.codex                              -> /home/codex/.codex
~/.claude                             -> /home/codex/.claude
~/.ssh                                -> /home/codex/.ssh:ro
~/.gitconfig                          -> /home/codex/.gitconfig:ro
~/.git-credentials                    -> /home/codex/.git-credentials:ro
~/.gnupg                              -> /home/codex/.gnupg:ro
~/.claude.json                        -> /home/codex/.claude.json
~/.cache/codex-container/npm          -> /home/codex/.npm
~/.cache/codex-container/pip          -> /home/codex/.cache/pip
~/.cache/codex-container/cargo        -> /home/codex/.cargo
~/.cache/codex-container/go           -> /home/codex/go
~/.cache/codex-container/maven        -> /home/codex/.m2
~/.cache/codex-container/gradle       -> /home/codex/.gradle
~/.cache/codex-container/cache        -> /cache
```

SSH, Git config, Git credentials, and GnuPG mounts are conditional. Missing files or directories are skipped.

## Permissions

The launcher passes the host user's UID and GID into the container:

```text
CODEX_UID=$(id -u)
CODEX_GID=$(id -g)
```

The container entrypoint creates a `codex` user with those IDs and runs the command as that user.

This prevents files created inside the mounted repository from becoming owned by root on the host.

## Options

Show help:

```bash
/workspace/codex-container/codex-container --help
```

Use Claude Code:

```bash
/workspace/codex-container/codex-container --agent claude
```

Run against another repository:

```bash
/workspace/codex-container/codex-container --repo /path/to/repo
```

Use another image:

```bash
/workspace/codex-container/codex-container --image my-codex:dev
```

Use another persistent home:

```bash
/workspace/codex-container/codex-container --home ~/.cache/my-codex-home
```

Skip SSH mounting:

```bash
/workspace/codex-container/codex-container --no-ssh
```

Skip Git config mounting:

```bash
/workspace/codex-container/codex-container --no-gitconfig
```

Mount the host Docker socket:

```bash
/workspace/codex-container/codex-container --docker
```

The Docker socket is not mounted by default. Mounting it gives the container broad control over the host Docker daemon.

## Environment Variables

The launcher also supports environment variables:

```text
CODEX_IMAGE             Docker image name. Default: codex-universal:latest
CODEX_REPO_DIR          Repository directory. Default: current directory
CODEX_AGENT             Agent to start: codex or claude. Default: codex
CODEX_CONTAINER_NAME    Container name. Default: codex-<repo-name>
CODEX_CONTAINER_HOME    Persistent /home/codex path. Default: ~/.cache/codex-container/home
CODEX_CACHE_ROOT        Cache root. Default: ~/.cache/codex-container
CODEX_MOUNT_DOCKER      Set to 1 to mount /var/run/docker.sock
```

Examples:

```bash
CODEX_AGENT=claude codex-container
CODEX_IMAGE=codex-universal:dev codex-container
CODEX_MOUNT_DOCKER=1 codex-container
```

## Authentication

Codex configuration is expected at:

```text
~/.codex
```

Claude Code configuration is expected at:

```text
~/.claude
~/.claude.json
```

These files are mounted from the host. They are not copied into the image.

If an agent needs initial login, start it once through the container and complete the login flow:

```bash
codex-container
codex-container --agent claude
```

The resulting state should persist in the mounted host directories.

## Smoke Test

After building the image:

```bash
mkdir -p /tmp/codex-container-test
cd /tmp/codex-container-test
/workspace/codex-container/codex-container bash -lc 'id && pwd && command -v codex && command -v claude && command -v rg && command -v fd && touch permission-test && ls -l permission-test'
```

Expected checks:

- `pwd` is `/workspace/repo`
- `codex` is available
- `claude` is available
- `rg` and `fd` are available
- `permission-test` is owned by the host user UID/GID, not root

## Files

```text
Dockerfile              Builds the universal Codex and Claude Code image
codex-entrypoint.sh     Creates the non-root runtime user and drops privileges
codex-container         Host launcher that mounts the current repository and user config
README.md               Usage guide
```
