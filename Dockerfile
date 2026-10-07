# Ubuntu 24.04 ships Python 3.12 as its system Python.  Project virtual
# environments may contain an absolute link to /usr/bin/python3.12, so the
# image must provide that interpreter rather than the Python 3.10 from 22.04.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV CODEX_NON_INTERACTIVE=1
ENV PATH="/usr/local/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    build-essential \
    ca-certificates \
    curl \
    fd-find \
    file \
    git \
    git-lfs \
    gnupg \
    gosu \
    htop \
    iproute2 \
    iputils-ping \
    jq \
    less \
    lsof \
    make \
    nano \
    netcat-openbsd \
    openssh-client \
    pkg-config \
    procps \
    python3 \
    python3.12 \
    python3-pip \
    python3-venv \
    python3.12-venv \
    ripgrep \
    rsync \
    sqlite3 \
    sudo \
    tree \
    unzip \
    vim-tiny \
    bubblewrap \
    wget \
    zip \
    xz-utils \
  && rm -rf /var/lib/apt/lists/*

# Keep the image contract explicit: venvs created against Python 3.12 must be
# usable inside the container.
RUN test -x /usr/bin/python3.12 \
  && python3.12 --version \
  && python3.12 -m venv --clear /tmp/python312-venv \
  && /tmp/python312-venv/bin/python --version \
  && rm -rf /tmp/python312-venv

RUN groupadd --system codex-sudo \
  && echo '%codex-sudo ALL=(ALL:ALL) NOPASSWD: ALL' \
    > /etc/sudoers.d/codex-container \
  && chmod 0440 /etc/sudoers.d/codex-container \
  && visudo -cf /etc/sudoers.d/codex-container

RUN install -d -m 0755 /etc/apt/keyrings \
  && curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc \
  && chmod a+r /etc/apt/keyrings/docker.asc \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
    docker-buildx-plugin \
    docker-ce-cli \
    docker-compose-plugin \
  && rm -rf /var/lib/apt/lists/*

RUN install -d -m 0755 /etc/apt/keyrings \
  && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    -o /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends gh \
  && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get update \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*

# Install Chromium's shared libraries, fonts, and headless-rendering dependencies.
RUN npx --yes playwright install-deps chromium \
  && npm cache clean --force \
  && rm -rf /var/lib/apt/lists/*

RUN install -d -m 0755 /etc/apt/keyrings \
  && curl -fsSL https://downloads.claude.ai/keys/claude-code.asc \
    -o /etc/apt/keyrings/claude-code.asc \
  && echo "deb [signed-by=/etc/apt/keyrings/claude-code.asc] https://downloads.claude.ai/claude-code/apt/stable stable main" \
    > /etc/apt/sources.list.d/claude-code.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends claude-code \
  && rm -rf /var/lib/apt/lists/*

ARG CODEX_VERSION=latest
ARG CODEX_CACHE_BUST=0
RUN echo "Installing Codex ${CODEX_VERSION} (cache bust: ${CODEX_CACHE_BUST})" \
  && npm install -g "@openai/codex@${CODEX_VERSION}"

# Ubuntu 24.04 marks the system Python as externally managed (PEP 668).
# These are image-provided CLI tools, so install them into that environment.
RUN pip3 install --break-system-packages --no-cache-dir \
    beautifulsoup4 httpx ruff pytest requests

RUN ln -sf /usr/bin/fdfind /usr/local/bin/fd

COPY codex-entrypoint.sh /usr/local/bin/codex-entrypoint
RUN chmod +x /usr/local/bin/codex-entrypoint

WORKDIR /workspace/repo

ENTRYPOINT ["codex-entrypoint"]
CMD ["codex"]
