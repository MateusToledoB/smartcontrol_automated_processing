FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    HEADLESS=true

WORKDIR /app

# Dependências do sistema
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

# Instala Edge
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge.list && \
    apt-get update && apt-get install -y --no-install-recommends microsoft-edge-stable && \
    rm -rf /var/lib/apt/lists/*

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

CMD ["python", "interfaces/workers/problema_no_equipamento.py"]
CMD ["python", "interfaces/workers/temporarios.py"]