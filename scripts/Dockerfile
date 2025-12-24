FROM python:3.13-slim

WORKDIR /app

# Install requests library
RUN pip install --no-cache-dir requests

# Copy the seed script
COPY seed-orders.py .

# Make script executable
RUN chmod +x seed-orders.py

CMD ["python", "seed-orders.py"]
