# Codex Container

这是一个通用 Docker 编程环境，可以在任意本地仓库中运行 Codex 和 Claude Code。

镜像内包含：

- OpenAI Codex CLI：`codex`
- Anthropic Claude Code CLI：`claude`
- 常用开发工具：`git`、`git-lfs`、`ripgrep`、`fd`、`python3`、`pip`、`venv`、`build-essential`、`docker`、`jq`、`openssh-client` 和基础编辑器

镜像不会内置 Codex 或 Claude 的凭据。运行时配置会从宿主机挂载进容器。

## 构建镜像

可以在任意目录执行：

```bash
docker build -t codex-universal:latest /workspace/codex-container
```

也可以在本目录执行：

```bash
docker build -t codex-universal:latest .
```

## 启动 Codex

进入任意仓库：

```bash
cd /path/to/repo
/workspace/codex-container/codex-container
```

如果已经把启动脚本放到 `PATH`：

```bash
cd /path/to/repo
codex-container
```

## 启动 Claude Code

```bash
cd /path/to/repo
/workspace/codex-container/codex-container --agent claude
```

如果已经把启动脚本放到 `PATH`：

```bash
cd /path/to/repo
codex-container --agent claude
```

## 进入 Shell

```bash
cd /path/to/repo
/workspace/codex-container/codex-container bash
```

- 使用 YOLO MODE 启动 codex

```bash
codex --ask-for-approval never --sandbox danger-full-access
```

## 安装启动脚本

这一步是可选的，但会更方便：

```bash
sudo ln -sf /workspace/codex-container/codex-container /usr/local/bin/codex-container
```

之后可以直接使用：

```bash
cd /path/to/repo
codex-container
codex-container --agent claude
codex-container bash
```

## 运行时目录

当前仓库会被挂载到：

```text
/workspace/repo
```

容器启动后的工作目录也是：

```text
/workspace/repo
```

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
当前仓库                              -> /workspace/repo
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

SSH、Git 配置、Git 凭据和 GnuPG 都是条件挂载。对应文件或目录不存在时会自动跳过。

## 文件权限

启动脚本会把宿主机当前用户的 UID 和 GID 传进容器：

```text
CODEX_UID=$(id -u)
CODEX_GID=$(id -g)
```

容器入口脚本会用这两个 ID 创建 `codex` 用户，并以这个用户运行命令。

这样可以避免容器在挂载的仓库中创建 root 所有的文件。

## 以 root 运行

如果需要以 root 用户运行容器，可以使用 `--user` 参数：

```bash
docker run --rm -it --user root -v /path/to/repo:/workspace/repo codex-universal:latest bash

docker exec -it --user root <container-id> bash
```

## 参数

查看帮助：

```bash
/workspace/codex-container/codex-container --help
```

使用 Claude Code：

```bash
/workspace/codex-container/codex-container --agent claude
```

指定另一个仓库：

```bash
/workspace/codex-container/codex-container --repo /path/to/repo
```

使用另一个镜像：

```bash
/workspace/codex-container/codex-container --image my-codex:dev
```

指定另一个持久化 home：

```bash
/workspace/codex-container/codex-container --home ~/.cache/my-codex-home
```

不挂载 SSH：

```bash
/workspace/codex-container/codex-container --no-ssh
```

不挂载 Git 配置：

```bash
/workspace/codex-container/codex-container --no-gitconfig
```

挂载宿主机 Docker socket：

```bash
/workspace/codex-container/codex-container --docker
```

Docker socket 默认不会挂载。挂载它之后，容器会获得对宿主机 Docker daemon 的高权限访问能力。

## 环境变量

启动脚本也支持这些环境变量：

```text
CODEX_IMAGE             Docker 镜像名。默认：codex-universal:latest
CODEX_REPO_DIR          仓库目录。默认：当前目录
CODEX_AGENT             启动的 agent：codex 或 claude。默认：codex
CODEX_CONTAINER_NAME    容器名。默认：codex-<repo-name>
CODEX_CONTAINER_HOME    持久化 /home/codex 路径。默认：~/.cache/codex-container/home
CODEX_CACHE_ROOT        缓存根目录。默认：~/.cache/codex-container
CODEX_MOUNT_DOCKER      设置为 1 时挂载 /var/run/docker.sock
```

示例：

```bash
CODEX_AGENT=claude codex-container
CODEX_IMAGE=codex-universal:dev codex-container
CODEX_MOUNT_DOCKER=1 codex-container
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

这些文件会从宿主机挂载进容器，不会复制进镜像。

如果某个 agent 需要首次登录，可以通过容器启动一次并完成登录流程：

```bash
codex-container
codex-container --agent claude
```

登录后的状态会保存在挂载的宿主机目录中。

## 冒烟测试

构建镜像后可以运行：

```bash
mkdir -p /tmp/codex-container-test
cd /tmp/codex-container-test
/workspace/codex-container/codex-container bash -lc 'id && pwd && command -v codex && command -v claude && command -v rg && command -v fd && touch permission-test && ls -l permission-test'
```

预期检查结果：

- `pwd` 是 `/workspace/repo`
- `codex` 可用
- `claude` 可用
- `rg` 和 `fd` 可用
- `permission-test` 属于宿主机用户 UID/GID，而不是 root

## 文件说明

```text
Dockerfile              构建通用 Codex 和 Claude Code 镜像
codex-entrypoint.sh     创建非 root 运行用户并降权执行命令
codex-container         宿主机启动脚本，负责挂载当前仓库和用户配置
README.md               英文使用说明
README.zh-CN.md         中文使用说明
```
