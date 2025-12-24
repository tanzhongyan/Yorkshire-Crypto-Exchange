# Use simpler production build approach
FROM node:23-slim

WORKDIR /app

# Copy package files (including lock file)
COPY yorkshire-crypto-exchange/package.json ./
COPY yorkshire-crypto-exchange/package-lock.json ./

# Install dependencies using locked versions
RUN npm ci --legacy-peer-deps

# Copy application files
COPY yorkshire-crypto-exchange/ .

# Build the application
RUN npm run build

# Set environment
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

EXPOSE 3000

# Start using Next's built-in server
CMD ["npm", "start"]