# 🏠 Leilão Insights

O **Leilão Insights** é uma plataforma de inteligência imobiliária projetada para investidores que desejam analisar ativos da Caixa Econômica Federal com precisão cirúrgica. O sistema evoluiu de scripts básicos para uma aplicação fullstack robusta, oferecendo indicadores financeiros avançados e uma interface premium.

## 🌟 Principais Funcionalidades

- **Dashboard de Indicadores**: Visualização em tempo real do total de imóveis, cidades cobertas, **Média** e **Mediana** de avaliação baseadas nos filtros aplicados.
- **Filtros Inteligentes**: Cascata geográfica (Estado -> Cidade -> Bairro) e filtragem por Modalidade de Venda com contagem dinâmica de itens.
- **Ordenação Dinâmica**: Organize imóveis por maior ou menor preço instantaneamente.
- **Cards de Alta Densidade**: Informações críticas extraídas via Regex (Quartos, Vagas, Área, Matrícula, Inscrição Imobiliária e Aceite de FGTS).
- **Design Premium**: Interface Light moderna focada em legibilidade e experiência do usuário profissional.

## 🏗️ Arquitetura do Sistema

- **Pipeline de Dados (Python)**: `extrai.py` e `ingest.py` para scraping e ingestão no banco de dados.
- **Backend (Node.js + Express + TypeScript)**: API de alta performance conectada ao PostgreSQL.
- **Frontend (React + Vite + Tailwind CSS)**: Aplicação SPA moderna com animações via Framer Motion.
- **Infraestrutura**: Dockerizada e pronta para deploy via Docker Compose ou Easypanel.

## 🚀 Como Executar Localmente

### Pré-requisitos

- Node.js 20+
- Python 3.12+ (uv recomendado)
- PostgreSQL instalado e rodando

### 1. Configuração do Ambiente

Crie um arquivo `.env` na raiz do projeto com suas credenciais:

```env
host=seu_host_postgres
port=5432
user="seu_usuario"
password="sua_password"
database="db_leiloes"
```

### 2. Backend

```bash
cd backend
npm install
npm run dev
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

## 🐳 Docker & Deploy

Para rodar o projeto completo via Docker:

```bash
docker-compose up -d --build
```

### Deploy na VPS (Easypanel)

Este repositório está otimizado para o **Easypanel**:

1.  Conecte o repositório `leilao_insights`.
2.  O Dockerfile do backend está em `./backend`.
3.  O Dockerfile do frontend está em `./frontend` (serve via Nginx).
4.  Configure `VITE_API_BASE` no build do frontend para apontar para a URL da sua API.

## ⚙️ Tecnologias

- **Linguagens**: TypeScript, JavaScript, Python.
- **Backend**: Express, node-postgres (pg).
- **Frontend**: React, Lucide-React, Framer Motion, Axios, React-Select.
- **Estilização**: Tailwind CSS.
- **Banco de Dados**: PostgreSQL e DuckDB (cache local).

---

Desenvolvido para análise de alta performance. 🚀🏠
