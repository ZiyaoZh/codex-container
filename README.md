# Codex Container

Universal Docker environment for running Codex and Claude Code against any local repository.

The image contains:

- OpenAI Codex CLI: `codex`
- Anthropic Claude Code CLI: `claude`
- GitHub CLI: `gh`
- Node.js 20 and `npm`
- Common development tools: `git`, `git-lfs`, `ripgrep`, `fd`, `python3`, `pip`, `venv`, `build-essential`, Docker CLI, Docker Compose v2, Docker Buildx, `jq`, `sqlite3`, `curl`, `wget`, `rsync`, `tree`, `zip`, `unzip`, `openssh-client`, and basic editors
- Troubleshooting tools: `file`, `htop`, `ip`, `ping`, `nc`, `lsof`, and `ps`

The image does not bake in Codex, Claude, Docker, GitHub, SSH, Git, or GnuPG credentials. Runtime configuration is mounted from the host.

## Build

From this directory:

```bash
docker build -t codex-universal:latest .
```

From any directory:

```bash
docker build -t codex-universal:latest /path/to/codex-container
```

## Update Codex

Update the Codex CLI in the image with one command:

```bash
codex-container --update
```

The launcher rebuilds `codex-universal:latest`, reuses the cached system dependency layers, and forces the latest `@openai/codex` package to be installed. The next container started with `codex-container` uses the updated image.

To update a differently named image:

```bash
codex-container --image my-codex:dev --update
```

## Run Codex

In any repository:

```bash
cd /path/to/repo
/path/to/codex-container/codex-container
```

If the launcher is on your `PATH`:

```bash
cd /path/to/repo
codex-container
```

You can start additional sessions from other terminals in the same repository:

```bash
codex-container codex
```

The first session creates the named container. Later sessions reuse that running container with `docker exec`, so multiple Codex, Claude, shell, or custom command processes can run in it concurrently. Mount-related options are determined by the first session and cannot be changed by later sessions until that container exits.

Older launcher versions could append an unintended trailing `-` to the default container name. The corrected launcher uses `codex-<repo-name>` exactly, so it can create a clean replacement alongside an older running container whose name ends in `-`.

## Docker Access

When the launcher runs on a host where `/var/run/docker.sock` exists, Docker access is enabled automatically for the first session:

```bash
codex-container
```

The launcher mounts the host socket, maps its group ID to the non-root `codex` user, conditionally mounts the host `~/.docker` configuration, and mounts the repository at its original host path so Compose bind mounts resolve correctly. Use `--docker` to require this setup and fail immediately when the host socket is unavailable:

```bash
codex-container --docker
```

Verify the complete setup with:

```bash
codex-container --docker bash -lc 'id && docker info && docker compose version && docker buildx version'
```

Use `--no-docker` or `CODEX_MOUNT_DOCKER=0` to keep the socket out of the container. Docker socket access gives the coding agent broad control over the host daemon, including the ability to start privileged containers and mount host paths, so only enable it for trusted repositories and sessions.

Docker mount choices are fixed by the first session for a named container. If a running container has the opposite setting, exit its active sessions before restarting with `--docker` or `--no-docker`.

## Run Claude Code

```bash
cd /path/to/repo
/path/to/codex-container/codex-container --agent claude
```

If the launcher is on your `PATH`:

```bash
cd /path/to/repo
codex-container --agent claude
```

## Open A Shell

```bash
cd /path/to/repo
/path/to/codex-container/codex-container bash
```

## Full Access Codex

For a fully unattended local session, pass Codex its approval and sandbox flags inside the container:

```bash
codex-container codex --ask-for-approval never --sandbox danger-full-access
```

This gives the agent broad access to the mounted repository and container environment. Only use it in repositories and containers where that level of access is acceptable.

## Install The Launcher

Optional, but convenient:

```bash
sudo ln -sf /path/to/codex-container/codex-container /usr/local/bin/codex-container
```

Then use:

```bash
cd /path/to/repo
codex-container
codex-container --agent claude
codex-container bash
```

## Runtime Layout

The selected repository is mounted here:

```text
/workspace/repo
```

Normally, the container runs with this working directory:

```text
/workspace/repo
```

When Docker access is enabled, the repository is also mounted at the same absolute path it has on the host, and that path becomes the working directory. The `/workspace/repo` mount remains available for compatibility. Matching paths are required because bind mounts are resolved by the host Docker daemon rather than inside the agent container.

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
current repo                          -> /workspace/repo
~/.cache/codex-container/home          -> /home/codex
~/.codex                               -> /home/codex/.codex
~/.claude                              -> /home/codex/.claude
~/.config/gh                           -> /home/codex/.config/gh
~/.ssh                                 -> /home/codex/.ssh:ro
~/.gitconfig                           -> /home/codex/.gitconfig:ro
~/.git-credentials                     -> /home/codex/.git-credentials:ro
~/.gnupg                               -> /home/codex/.gnupg:ro
~/.claude.json                         -> /home/codex/.claude.json
~/.cache/codex-container/npm           -> /home/codex/.npm
~/.cache/codex-container/pip           -> /home/codex/.cache/pip
~/.cache/codex-container/cargo         -> /home/codex/.cargo
~/.cache/codex-container/go            -> /home/codex/go
~/.cache/codex-container/maven         -> /home/codex/.m2
~/.cache/codex-container/gradle        -> /home/codex/.gradle
~/.cache/codex-container/cache         -> /cache
```

When the host Docker socket is enabled, the launcher additionally mounts:

```text
/var/run/docker.sock                   -> /var/run/docker.sock
absolute host repository path          -> same absolute container path
~/.docker                              -> /home/codex/.docker
```

The `~/.docker` mount is conditional. If the host directory does not exist, Docker creates and uses configuration inside the persistent container home instead.

SSH, Git config, Git credentials, GnuPG, and Claude JSON mounts are conditional. Missing files or directories are skipped. Codex, Claude, and GitHub CLI config directories are created on the host if they do not exist.

## Permissions

The launcher passes the host user's UID and GID into the container:

```text
CODEX_UID=$(id -u)
CODEX_GID=$(id -g)
```

The container entrypoint creates a `codex` user with those IDs and runs the command as that user.

This prevents files created inside the mounted repository from becoming owned by root on the host.

When Docker access is enabled, the entrypoint reads the group ID of `/var/run/docker.sock` and adds the `codex` user to a matching supplementary group. This allows Docker commands while the agent itself continues to run as `codex`.

## Run As Root

The default entrypoint intentionally drops from root to the `codex` user. To start a one-off root shell, bypass the entrypoint:

```bash
docker run --rm -it \
  --user root \
  --entrypoint bash \
  -v /path/to/repo:/workspace/repo \
  -w /workspace/repo \
  codex-universal:latest
```

To enter an already running container as root:

```bash
docker exec -it --user root <container-name-or-id> bash
```

## Options

Show help:

```bash
codex-container --help
```

Use Claude Code:

```bash
codex-container --agent claude
```

Run against another repository:

```bash
codex-container --repo /path/to/repo
```

Use another image:

```bash
codex-container --image my-codex:dev
```

Set the container name:

```bash
codex-container --name my-codex-session
```

Use another persistent home:

```bash
codex-container --home ~/.cache/my-codex-home
```

Skip SSH mounting:

```bash
codex-container --no-ssh
```

Skip Git config mounting:

```bash
codex-container --no-gitconfig
```

Require the Docker CLI, Compose, and Buildx through the host Docker socket:

```bash
codex-container --docker
```

Docker access is normally enabled automatically when the socket exists. `--docker` makes the socket mandatory. A later session cannot add it to an already-running container, so exit the active sessions and recreate the container if it was initially started without Docker access.

Explicitly disable automatic Docker socket mounting:

```bash
codex-container --no-docker
```

## Environment Variables

The launcher also supports environment variables:

```text
CODEX_IMAGE             Docker image name. Default: codex-universal:latest
CODEX_REPO_DIR          Repository directory. Default: current directory
CODEX_AGENT             Agent to start: codex or claude. Default: codex
CODEX_CONTAINER_NAME    Container name. Default: codex-<repo-name>
CODEX_CONTAINER_HOME    Persistent /home/codex path. Default: ~/.cache/codex-container/home
CODEX_CACHE_ROOT        Cache root. Default: ~/.cache/codex-container
CODEX_MOUNT_DOCKER      auto, 1, or 0. Default: auto
```

Examples:

```bash
CODEX_AGENT=claude codex-container
CODEX_IMAGE=codex-universal:dev codex-container
CODEX_MOUNT_DOCKER=1 codex-container
CODEX_MOUNT_DOCKER=0 codex-container
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

GitHub CLI configuration is expected at:

```text
~/.config/gh
```

These files and directories are mounted from the host. They are not copied into the image.

If an agent or tool needs initial login, start it once through the container and complete the login flow:

```bash
codex-container
codex-container --agent claude
codex-container bash -lc 'gh auth status || gh auth login'
```

The resulting state persists in the mounted host directories.

## Smoke Test

After building the image:

```bash
mkdir -p /tmp/codex-container-test
cd /tmp/codex-container-test
codex-container bash -lc 'id && pwd && command -v codex && command -v claude && command -v gh && command -v rg && command -v fd && command -v node && command -v python3 && touch permission-test && ls -l permission-test'
```

Expected checks:

- `pwd` is `/workspace/repo`
- `codex` is available
- `claude` is available
- `gh` is available
- `rg` and `fd` are available
- `node` and `python3` are available
- `permission-test` is owned by the host user UID/GID, not root

When the host Docker socket is available, verify Docker separately:

```bash
codex-container --docker bash -lc 'docker info && docker run --rm hello-world && docker compose version && docker buildx version'
```

## Files

```text
Dockerfile              Builds the universal Codex and Claude Code image
codex-entrypoint.sh     Creates the non-root runtime user and drops privileges
codex-container         Host launcher that mounts the current repository and user config
README.md               English usage guide
README.zh-CN.md         Chinese usage guide
```
