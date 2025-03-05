# Use official Node.js image
FROM node:23-slim

# Set working directory
WORKDIR /app

# Copy dependencies
COPY package.json ./
RUN npm install

# Copy all files
COPY . .

# Expose port 8080
EXPOSE 8080

# Start Vue application
CMD ["npm", "run", "serve"]