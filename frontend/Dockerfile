# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./

# Usa npm install em vez de npm ci para evitar falha quando o package-lock.json
# está levemente desatualizado em relação ao package.json (ex: minor bumps de eslint/typescript-eslint)
RUN npm install

COPY . .

# VITE_API_URL vazio = usa proxy do nginx (/api/ -> backend:8000)
# Sobrescreve qualquer valor que possa estar no .env copiado acima
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ── Stage 2: Serve com Nginx ──────────────────────────────────────────────────
# Pin de patch do Alpine para reproducibilidade do build.
# CVE-2026-42055/9256/49975: falsos positivos para nginx 1.28.x
# (ver .trivyignore para justificativa detalhada)
FROM nginx:1.28-alpine3.23 AS runtime

RUN apk upgrade --no-cache \
    && rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
