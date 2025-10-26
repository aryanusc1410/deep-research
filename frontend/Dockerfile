FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files from frontend/
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source
COPY frontend/ .
RUN npm run build

# Production image
FROM node:18-alpine

WORKDIR /app

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./

EXPOSE 3000

CMD ["npm", "start"]