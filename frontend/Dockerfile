FROM node:18-alpine AS deps
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci --legacy-peer-deps

# ---- Dev image ----
FROM node:18-alpine AS dev
WORKDIR /app

# Copy package files first
COPY package.json package-lock.json* ./

# Install dependencies directly in dev stage for volume mount compatibility
RUN npm ci --legacy-peer-deps

# Copy application code
COPY . .

EXPOSE 3000

# Use npm run dev as default, but can be overridden
CMD ["npm", "run", "dev"]

# ---- Prod image ----
FROM node:18-alpine AS prod
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Copy node_modules from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy application code
COPY . .

# Build the application
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"] 