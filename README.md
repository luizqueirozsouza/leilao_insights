# Imóveis Caixa - Fullstack Pipeline

Este projeto evoluiu de um simples script Streamlit para uma aplicação fullstack moderna. Ele automatiza a extração, processamento e visualização premium dos imóveis da Caixa.

## 🏗️ Arquitetura

- **Data Pipeline (Python)**: `extrai.py` e `ingest.py` (Scraping e Ingestão DuckDB).
- **Backend (Node.js + TypeScript)**: API Express rodando em `localhost:3001` que serve dados do DuckDB.
- **Frontend (React + Vite + Tailwind)**: Dashboard moderno e responsivo com filtros inteligentes.

---

## 🚀 Como Executar

O projeto agora está dividido em três partes principais:

### 1. Extração e Ingestão (Python)

Continue usando o `uv` para manter o banco de dados atualizado:

```bash
uv run extrai.py
uv run ingest.py
```

### 2. Backend (Node.js)

Inicia a API que conecta o banco de dados ao frontend:

```bash
cd backend
npm install
npm run dev
```

### 3. Frontend (React)

Inicia a interface visual premium:

```bash
cd frontend
npm install
npm run dev
```

---

## 🛠️ Tecnologias Utilizadas

- **Backend**: Node.js, Express, DuckDB-Node, TypeScript.
- **Frontend**: React 18, Vite, Tailwind CSS, Framer Motion (animações), Lucide React (ícones).
- **Database**: DuckDB (armazenamento de alta performance).

## 📝 Notas de Desenvolvimento

- O backend serve a API em `http://localhost:3001/api/properties`.
- O frontend consome essa API e aplica filtros dinâmicos.
- O visual utiliza **Glassmorphism** e o esquema de cores oficial da Caixa.
