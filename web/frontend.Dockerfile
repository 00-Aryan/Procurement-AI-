# Stage 1: Install dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY web/package.json web/package-lock.json ./
RUN npm ci

# Stage 2: Build the Next.js application
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./web/node_modules
COPY . .
WORKDIR /app/web
RUN npm run build

# Stage 3: Run the production server
FROM node:20-alpine AS runner
WORKDIR /app/web
ENV NODE_ENV=production

# Copy built artifacts and runtime dependencies
COPY --from=builder /app/web/package.json /app/web/package-lock.json ./
COPY --from=builder /app/web/node_modules ./node_modules
COPY --from=builder /app/web/.next ./.next
COPY --from=builder /app/web/public ./public
COPY --from=builder /app/industry-config.json /app/industry-config.json

EXPOSE 3001
CMD ["npm", "run", "start", "--", "-p", "3001"]
