FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    HEADLESS=true \
    CHROME_HEADLESS_SHELL_PATH=/opt/chrome-headless-shell/chrome-headless-shell-linux64/chrome-headless-shell \
    CHROMEDRIVER_PATH=/opt/chromedriver/chromedriver-linux64/chromedriver

WORKDIR /app

# Dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    tini \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Instala chrome-headless-shell + chromedriver (Chrome for Testing).
# chrome-headless-shell e um binario so-headless, sem a stack de UI (GTK/X11)
# do navegador completo, o que reduz bastante o consumo de RAM/CPU por instancia
# ao rodar varios bots (drivers) em paralelo no servidor.
ARG CHROME_FOR_TESTING_VERSION=150.0.7871.46
RUN mkdir -p /opt/chrome-headless-shell /opt/chromedriver && \
    curl -fsSL -o /tmp/chrome-headless-shell.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_FOR_TESTING_VERSION}/linux64/chrome-headless-shell-linux64.zip" && \
    curl -fsSL -o /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_FOR_TESTING_VERSION}/linux64/chromedriver-linux64.zip" && \
    unzip -q /tmp/chrome-headless-shell.zip -d /opt/chrome-headless-shell && \
    unzip -q /tmp/chromedriver.zip -d /opt/chromedriver && \
    chmod +x "$CHROME_HEADLESS_SHELL_PATH" "$CHROMEDRIVER_PATH" && \
    rm /tmp/chrome-headless-shell.zip /tmp/chromedriver.zip

# Instala uv
RUN pip install --no-cache-dir uv

# Copia deps
COPY pyproject.toml uv.lock ./

# Instala dependências
RUN uv venv /app/.venv && \
    uv sync --frozen --no-dev

# Copia projeto
COPY . .

ENV PATH="/app/.venv/bin:${PATH}"

COPY start.sh .

RUN chmod +x start.sh

# tini como PID 1: recolhe processos orfaos (ex: chrome-headless-shell reparentado
# apos o chromedriver morrer) para nao acumular zumbis no container.
ENTRYPOINT ["tini", "--"]
CMD ["sh", "start.sh"]
