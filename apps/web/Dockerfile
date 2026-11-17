FROM node:22.22.0-alpine AS build

RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/ui/package.json packages/ui/package.json
RUN pnpm install --frozen-lockfile
COPY apps/web apps/web
COPY packages/ui packages/ui

ARG VITE_API_URL=/api
ARG VITE_INTERNAL_USER_ID=10000000-0000-0000-0000-000000000001
ENV VITE_API_URL=$VITE_API_URL \
    VITE_INTERNAL_USER_ID=$VITE_INTERNAL_USER_ID
RUN pnpm --filter @repwise/web build

FROM nginx:1.29.3-alpine
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/web/dist /usr/share/nginx/html
EXPOSE 8080
