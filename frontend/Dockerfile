# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./

# npm ci requires package-lock.json — ensures reproducible installs
RUN npm ci

COPY . .

RUN npm run build

# ── Stage 2: Serve com Nginx ───────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Remove config padrão e copia a nossa
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copia o build gerado
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
