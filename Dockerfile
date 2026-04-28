FROM python:3.10-slim

WORKDIR /app

# Prevent python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 5000 5001 8080

# Default command: run orchestrator (override at runtime)
CMD ["python", "run_all.py"]
