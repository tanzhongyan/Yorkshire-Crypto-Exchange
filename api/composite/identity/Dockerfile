# Use official Python image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port 5000 for Flask
EXPOSE 5000

# Ensure migrations run before starting the service
CMD ["python","app.py"]
