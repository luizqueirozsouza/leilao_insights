# Build stage
FROM node:20-slim AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Variável de ambiente para o build do Vite
ARG VITE_API_BASE
ENV VITE_API_BASE=$VITE_API_BASE

RUN npm run build

# Production stage
FROM nginx:stable-alpine

# Copiar os arquivos buildados para o diretório do Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Configuração minimalista para Nginx lidar com rotas SPA se necessário
# RUN echo 'server { listen 80; location / { root /usr/share/nginx/html; index index.html; try_files $uri $uri/ /index.html; } }' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
