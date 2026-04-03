# Usar uma imagem Python leve
FROM python:3.13-slim

# Instalar dependências de sistema necessárias para compilar algumas libs (como psycopg2) e para o uv
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar o 'uv' para gerenciamento rápido de dependências
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Definir o diretório de trabalho
WORKDIR /app

# Copiar os arquivos de definição de dependências
COPY pyproject.toml uv.lock ./

# Instalar as dependências do projeto (usa cache se os arquivos acima não mudarem)
RUN uv sync --no-cache

# Copiar o restante do código do projeto para o container
COPY . .

# Expor a porta padrão do Streamlit
EXPOSE 8501

# Configurações do Streamlit para rodar em container
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Comando padrão: rodar o dashboard
# O usuário também pode rodar ingest ou extrai via 'docker-compose run'
CMD ["uv", "run", "streamlit", "run", "app.py"]
