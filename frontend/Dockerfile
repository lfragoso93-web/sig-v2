# ── Stage 1: Build ───────────────────────────────────────────────────────────────────────────────
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

# ── Stage 2: Serve com Nginx ───────────────────────────────────────────────────────────────────
# Pin de patch do Alpine para garantir que apk instale nginx>=1.28.3-r4
# (CVE-2026-42055 CRITICAL, fixed em 1.28.3-r4)
FROM nginx:1.28-alpine3.23 AS runtime

RUN apk upgrade --no-cache \
    && apk add --no-cache 'nginx>=1.28.3-r4' \
    && rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
