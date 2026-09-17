# syntax=docker/dockerfile:1

FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
# Force relative API base in production bundle to avoid hardcoded private IPs.
ARG PUBLIC_API_BASE=/presenze
ENV PUBLIC_API_BASE=${PUBLIC_API_BASE}
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
