# Codex Container

这是一个通用 Docker 编程环境，可以在任意本地仓库中运行 Codex 和 Claude Code。

镜像内包含：

- OpenAI Codex CLI：`codex`
- Anthropic Claude Code CLI：`claude`
- GitHub CLI：`gh`
- Node.js 20 和 `npm`
- 常用开发工具：`git`、`git-lfs`、`ripgrep`、`fd`、`python3`、`pip`、`venv`、`build-essential`、Docker CLI、Docker Compose v2、Docker Buildx、`jq`、`sqlite3`、`curl`、`wget`、`rsync`、`tree`、`zip`、`unzip`、`openssh-client` 和基础编辑器
- 排障工具：`file`、`htop`、`ip`、`ping`、`nc`、`lsof` 和 `ps`

镜像不会内置 Codex、Claude、Docker、GitHub、SSH、Git 或 GnuPG 的凭据。运行时配置会从宿主机挂载进容器。

## 构建镜像

在本目录执行：

```bash
docker build -t codex-universal:latest .
```

也可以在任意目录执行：

```bash
docker build -t codex-universal:latest /path/to/codex-container
```

## 一键更新 Codex

使用一条命令更新镜像内的 Codex CLI：

```bash
codex-container --update
```

启动脚本会重新构建 `codex-universal:latest`，复用已有的系统依赖缓存，并强制安装最新版本的 `@openai/codex`。之后通过 `codex-container` 启动的容器会直接使用更新后的镜像。

如果使用的是其他镜像名，可以执行：

```bash
codex-container --image my-codex:dev --update
```

## 启动 Codex

进入任意仓库：

```bash
cd /path/to/repo
/path/to/codex-container/codex-container
```

如果已经把启动脚本放到 `PATH`：

```bash
cd /path/to/repo
codex-container
```

可以在同一仓库的其他终端继续启动会话：

```bash
codex-container codex
```

第一个会话会创建具名容器，后续会话通过 `docker exec` 复用正在运行的容器，因此可以同时运行多个 Codex、Claude、Shell 或自定义命令进程。挂载相关参数由第一个会话决定，在该容器退出前，后续会话不能修改这些挂载配置。

旧版启动器可能会在默认容器名末尾错误地追加一个 `-`。修复后的名称严格为 `codex-<仓库名>`，因此可以在旧容器仍运行时创建一个名称正确的新容器，用于迁移到新的挂载配置。

## 使用 Docker

启动器运行在存在 `/var/run/docker.sock` 的宿主机上时，第一个会话会自动获得 Docker 能力：

```bash
codex-container
```

启动器会挂载宿主机 socket，把它的组 ID 映射给非 root 的 `codex` 用户，按需挂载宿主机的 `~/.docker` 配置，并按宿主机原始绝对路径再次挂载仓库，使 Compose 的 bind mount 能够正确解析。使用 `--docker` 可以强制要求该环境；宿主机 socket 不存在时会立即报错：

```bash
codex-container --docker
```

可以用下面的命令验证完整环境：

```bash
codex-container --docker bash -lc 'id && docker info && docker compose version && docker buildx version'
```

使用 `--no-docker` 或 `CODEX_MOUNT_DOCKER=0` 可以禁止挂载 socket。Docker socket 会让 coding agent 获得对宿主机 daemon 的高权限访问，包括启动特权容器和挂载宿主机路径，因此只应在可信仓库和会话中使用。

具名容器的 Docker 挂载状态由第一个会话决定。如果正在运行的容器与新传入的 `--docker` 或 `--no-docker` 设置相反，需要先退出其活动会话再重新启动。

## 启动 Claude Code

```bash
cd /path/to/repo
/path/to/codex-container/codex-container --agent claude
```

如果已经把启动脚本放到 `PATH`：

```bash
cd /path/to/repo
codex-container --agent claude
```

## 进入 Shell

```bash
cd /path/to/repo
/path/to/codex-container/codex-container bash
```

## 全权限 Codex

如果需要无人值守的本地会话，可以把 Codex 的 approval 和 sandbox 参数传给容器内的 `codex`：

```bash
codex-container codex --ask-for-approval never --sandbox danger-full-access
```

这会让 agent 对挂载的仓库和容器环境拥有较高权限。只应在你接受这种访问范围的仓库和容器中使用。

## 安装启动脚本

这一步是可选的，但会更方便：

```bash
sudo ln -sf /path/to/codex-container/codex-container /usr/local/bin/codex-container
```

之后可以直接使用：

```bash
cd /path/to/repo
codex-container
codex-container --agent claude
codex-container bash
```

## 运行时目录

指定的仓库会被挂载到：

```text
/workspace/repo
```

通常情况下，容器启动后的工作目录也是：

```text
/workspace/repo
```

启用 Docker 能力时，仓库还会按照它在宿主机上的绝对路径挂载一次，并将该路径设为工作目录；`/workspace/repo` 挂载仍会保留以兼容已有用法。这样做是因为 bind mount 路径由宿主机 Docker daemon 解析，而不是由 agent 容器解析。

容器用户 home 目录是：

```text
/home/codex
```

默认情况下，宿主机上的持久化 home 路径是：

```text
~/.cache/codex-container/home
```

这样即使容器使用 `--rm` 自动删除，agent 的运行状态也可以保留。

## 默认挂载

启动脚本会在路径存在时挂载这些宿主机路径：

```text
当前仓库                               -> /workspace/repo
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

启用宿主机 Docker socket 时还会增加以下挂载：

```text
/var/run/docker.sock                   -> /var/run/docker.sock
宿主机仓库绝对路径                     -> 容器内相同绝对路径
~/.docker                              -> /home/codex/.docker
```

`~/.docker` 是条件挂载；如果宿主机上不存在该目录，Docker 会改用持久化容器 home 中的配置。

SSH、Git 配置、Git 凭据、GnuPG 和 Claude JSON 都是条件挂载。对应文件或目录不存在时会自动跳过。Codex、Claude 和 GitHub CLI 的配置目录不存在时会在宿主机上自动创建。

## 文件权限

启动脚本会把宿主机当前用户的 UID 和 GID 传进容器：

```text
CODEX_UID=$(id -u)
CODEX_GID=$(id -g)
```

容器入口脚本会用这两个 ID 创建 `codex` 用户，并以这个用户运行命令。

这样可以避免容器在挂载的仓库中创建 root 所有的文件。

启用 Docker 能力后，入口脚本会读取 `/var/run/docker.sock` 的组 ID，并把 `codex` 用户加入对应的补充组。因此 agent 自身仍以 `codex` 用户运行，同时可以执行 Docker 命令。

## 以 root 运行

默认入口脚本会刻意从 root 降权到 `codex` 用户。如果需要启动一次性的 root shell，可以绕过入口脚本：

```bash
docker run --rm -it \
  --user root \
  --entrypoint bash \
  -v /path/to/repo:/workspace/repo \
  -w /workspace/repo \
  codex-universal:latest
```

如果要进入已经运行的容器：

```bash
docker exec -it --user root <container-name-or-id> bash
```

## 参数

查看帮助：

```bash
codex-container --help
```

使用 Claude Code：

```bash
codex-container --agent claude
```

指定另一个仓库：

```bash
codex-container --repo /path/to/repo
```

使用另一个镜像：

```bash
codex-container --image my-codex:dev
```

指定容器名：

```bash
codex-container --name my-codex-session
```

指定另一个持久化 home：

```bash
codex-container --home ~/.cache/my-codex-home
```

不挂载 SSH：

```bash
codex-container --no-ssh
```

不挂载 Git 配置：

```bash
codex-container --no-gitconfig
```

强制要求通过宿主机 Docker socket 使用 Docker CLI、Compose 和 Buildx：

```bash
codex-container --docker
```

宿主机 socket 存在时，Docker 能力通常会自动启用；`--docker` 会把 socket 设为必需条件。后续会话无法给已经运行的容器补加 socket，因此如果第一个会话未启用 Docker，需要退出所有活动会话并重新创建容器。

显式禁止自动挂载 Docker socket：

```bash
codex-container --no-docker
```

## 环境变量

启动脚本也支持这些环境变量：

```text
CODEX_IMAGE             Docker 镜像名。默认：codex-universal:latest
CODEX_REPO_DIR          仓库目录。默认：当前目录
CODEX_AGENT             启动的 agent：codex 或 claude。默认：codex
CODEX_CONTAINER_NAME    容器名。默认：codex-<repo-name>
CODEX_CONTAINER_HOME    持久化 /home/codex 路径。默认：~/.cache/codex-container/home
CODEX_CACHE_ROOT        缓存根目录。默认：~/.cache/codex-container
CODEX_MOUNT_DOCKER      auto、1 或 0。默认：auto
```

示例：

```bash
CODEX_AGENT=claude codex-container
CODEX_IMAGE=codex-universal:dev codex-container
CODEX_MOUNT_DOCKER=1 codex-container
CODEX_MOUNT_DOCKER=0 codex-container
```

## 登录和认证

Codex 配置默认来自：

```text
~/.codex
```

Claude Code 配置默认来自：

```text
~/.claude
~/.claude.json
```

GitHub CLI 配置默认来自：

```text
~/.config/gh
```

这些文件和目录会从宿主机挂载进容器，不会复制进镜像。

如果某个 agent 或工具需要首次登录，可以通过容器启动一次并完成登录流程：

```bash
codex-container
codex-container --agent claude
codex-container bash -lc 'gh auth status || gh auth login'
```

登录后的状态会保存在挂载的宿主机目录中。

## 冒烟测试

构建镜像后可以运行：

```bash
mkdir -p /tmp/codex-container-test
cd /tmp/codex-container-test
codex-container bash -lc 'id && pwd && command -v codex && command -v claude && command -v gh && command -v rg && command -v fd && command -v node && command -v python3 && touch permission-test && ls -l permission-test'
```

预期检查结果：

- `pwd` 是 `/workspace/repo`
- `codex` 可用
- `claude` 可用
- `gh` 可用
- `rg` 和 `fd` 可用
- `node` 和 `python3` 可用
- `permission-test` 属于宿主机用户 UID/GID，而不是 root

宿主机 Docker socket 可用时，可以单独验证 Docker：

```bash
codex-container --docker bash -lc 'docker info && docker run --rm hello-world && docker compose version && docker buildx version'
```

## 文件说明

```text
Dockerfile              构建通用 Codex 和 Claude Code 镜像
codex-entrypoint.sh     创建非 root 运行用户并降权执行命令
codex-container         宿主机启动脚本，负责挂载当前仓库和用户配置
README.md               英文使用说明
README.zh-CN.md         中文使用说明
```
