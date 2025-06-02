FROM node:18-alpine AS deps
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies (will create node_modules even without lockfile)
RUN npm install --legacy-peer-deps || true

# ---- Dev image ----
FROM node:18-alpine AS dev
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]

# ---- Prod image ----
FROM node:18-alpine AS prod
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"] 