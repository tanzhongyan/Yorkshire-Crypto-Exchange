FROM python:3.11-slim

WORKDIR /app

COPY rabbit_setup.py .

RUN pip install pika

CMD ["python", "rabbit_setup.py"]