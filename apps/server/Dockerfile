FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
      "fastapi>=0.116.1" \
      "uvicorn[standard]>=0.35.0" \
      "sqlalchemy>=2.0.43" \
      "psycopg[binary]>=3.2.6" \
      "pydantic>=2.10.6" \
      "python-multipart>=0.0.20" \
      "pillow>=11.3.0" \
      "requests>=2.32.0" \
      "joblib>=1.4.2" \
      "scikit-learn==1.6.1"

COPY app /app/app
COPY scripts /app/scripts
COPY worker.py /app/worker.py
COPY data /app/data
COPY main.py /app/main.py

EXPOSE 8000
