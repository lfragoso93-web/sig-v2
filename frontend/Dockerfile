# --- Stage 1: build React ---
FROM node:20-alpine AS builder

WORKDIR /app

# Instala dependencias (gera lock automaticamente se nao existir)
COPY package*.json ./
RUN npm install --frozen-lockfile || npm install

COPY . .
RUN npm run build

# --- Stage 2: Nginx serve ---
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
