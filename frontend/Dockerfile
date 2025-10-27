FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files from frontend/
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source
COPY frontend/ .

# Accept build arg and set as env var
ARG NEXT_PUBLIC_BACKEND_URL=https://deep-research-backend-zge9.onrender.com
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL

RUN npm run build

# Production image
FROM node:18-alpine

WORKDIR /app

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["npm", "start"]