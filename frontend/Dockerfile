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
# Nginx 1.30.4+ corrige a CVE-2026-42533 reportada pelo Trivy no runtime frontend.
FROM nginx:1.30.4-alpine3.24 AS runtime

# O nginx oficial inicia como root para bind em porta privilegiada. Mantemos a
# porta interna 80 por compatibilidade com Compose/Cloudflare, mas concedemos
# apenas CAP_NET_BIND_SERVICE ao binário e executamos o runtime como nginx.
RUN apk upgrade --no-cache \
    && apk add --no-cache libcap \
    && rm /etc/nginx/conf.d/default.conf \
    && touch /var/run/nginx.pid \
    && chown -R nginx:nginx \
        /var/cache/nginx \
        /var/run/nginx.pid \
        /etc/nginx/conf.d \
        /usr/share/nginx/html \
    && setcap 'cap_net_bind_service=+ep' /usr/sbin/nginx \
    && apk del libcap

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build --chown=nginx:nginx /app/dist /usr/share/nginx/html

USER nginx

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
