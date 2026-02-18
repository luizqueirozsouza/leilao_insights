FROM node:20-slim

WORKDIR /app

# Instalar dependências globais se necessário
# RUN npm install -g typescript ts-node

COPY package*.json ./
RUN npm install

COPY . .

# O backend usa TS, precisamos buildar
RUN npm run build

# Porta que o app vai rodar
EXPOSE 3001

# Comando para iniciar o servidor
CMD ["npm", "start"]
