FROM python:3.11-slim

WORKDIR /app

# Install core package first
COPY ../core /tmp/skillseed-core
RUN pip install --no-cache-dir /tmp/skillseed-core

# Install API package
COPY . .
RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
