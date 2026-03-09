FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Only copy what the redirect service needs at runtime
COPY config.py .
COPY redirect_service.py .
COPY data/mapping.csv data/mapping.csv

EXPOSE 8080

CMD ["uvicorn", "redirect_service:app", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--workers", "2", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
