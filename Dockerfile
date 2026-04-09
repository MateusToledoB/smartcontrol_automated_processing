FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    HEADLESS=true \
    EDGE_DRIVER_PATH=/usr/local/bin/msedgedriver

WORKDIR /app

# Dependencias de sistema para Selenium + Edge
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
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
    libgcc1 \
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

# Repositorio oficial do Microsoft Edge
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge.list && \
    apt-get update && apt-get install -y --no-install-recommends microsoft-edge-stable && \
    rm -rf /var/lib/apt/lists/*

# Instala msedgedriver no build (sem download em runtime), com fallback de URL
RUN set -eux; \
    EDGE_VERSION="$(microsoft-edge --version | awk '{print $3}')"; \
    DRIVER_URL_1="https://msedgedriver.azureedge.net/${EDGE_VERSION}/edgedriver_linux64.zip"; \
    DRIVER_URL_2="https://msedgewebdriverstorage.blob.core.windows.net/edgewebdriver/${EDGE_VERSION}/edgedriver_linux64.zip"; \
    if ! curl -fL --retry 3 --retry-delay 2 -o /tmp/edgedriver_linux64.zip "${DRIVER_URL_1}"; then \
      curl -fL --retry 3 --retry-delay 2 -o /tmp/edgedriver_linux64.zip "${DRIVER_URL_2}"; \
    fi; \
    unzip -q /tmp/edgedriver_linux64.zip -d /tmp; \
    mv /tmp/msedgedriver /usr/local/bin/msedgedriver; \
    chmod +x /usr/local/bin/msedgedriver; \
    rm -f /tmp/edgedriver_linux64.zip

# Instala uv
RUN pip install --no-cache-dir uv

# Copia apenas arquivos de dependencias primeiro (melhor cache de build)
COPY pyproject.toml uv.lock ./

# Cria venv e instala dependencias travadas no lock
RUN uv venv /app/.venv && \
    uv sync --frozen --no-dev

# Copia o restante do projeto
COPY . .

ENV PATH="/app/.venv/bin:${PATH}"

CMD ["python", "interfaces/workers/problema_no_equipamento.py"]
