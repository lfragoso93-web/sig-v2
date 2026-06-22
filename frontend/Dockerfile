# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./

RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .

# VITE_API_URL vazio = usa proxy do nginx (/api/ -> backend:8000)
# Sobrescreve qualquer valor que possa estar no .env copiado acima
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ── Stage 2: Serve com Nginx ──────────────────────────────────────────────────
# Pin de patch do Alpine para garantir repositorio com nginx>=1.28.3-r4
# (CVE-2026-42055 CRITICAL, fixed em 1.28.3-r4)
FROM nginx:1.28-alpine3.23 AS runtime

# Atualiza nginx e todos os seus modulos atomicamente para evitar conflito
# de dependencia entre nginx-r4 e nginx-module-*-r1.
# apk upgrade --no-cache cobre o restante do sistema.
RUN apk upgrade --no-cache nginx nginx-module-* \
    && apk upgrade --no-cache \
    && rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
