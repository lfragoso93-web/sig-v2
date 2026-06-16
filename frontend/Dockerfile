# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./

# Usa npm ci se package-lock.json existir, senão npm install
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .

RUN npm run build

# ── Stage 2: Serve com Nginx ──────────────────────────────────────────────────
# nginx:1.28-alpine usa Alpine 3.22 com openssl, libxml2, libpng, musl atualizados
# apk upgrade garante que qualquer pacote residual sem patch seja atualizado
FROM nginx:1.28-alpine AS runtime

RUN apk upgrade --no-cache \
    && rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copia o build gerado
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
