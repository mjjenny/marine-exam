# ── Frontend: build the Vite/React app, serve it with Nginx ──────────────
# Stage 1 — build the static assets
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2 — serve the built assets + reverse-proxy /api to the backend
FROM nginx:1.27-alpine
# Baked-in default config; docker-compose also mounts frontend/nginx.conf over this
# so you can edit it (e.g. add the HTTPS block) without rebuilding the image.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80 443
