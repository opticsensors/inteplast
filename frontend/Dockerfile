# Use the same npm lockfile as local development.
FROM node:22-bookworm-slim AS build-stage

WORKDIR /app

COPY package.json package-lock.json /app/

COPY frontend/package.json /app/frontend/

RUN npm ci

COPY ./frontend /app/frontend
WORKDIR /app/frontend
ARG VITE_API_URL

RUN npm run build


# Stage 1, based on Nginx, to have only the compiled app, ready for production with Nginx
FROM nginx:1

COPY --from=build-stage /app/frontend/dist/ /usr/share/nginx/html

COPY ./frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY ./frontend/nginx-backend-not-found.conf /etc/nginx/extra-conf.d/backend-not-found.conf
