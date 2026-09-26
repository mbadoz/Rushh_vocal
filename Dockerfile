FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libsndfile1 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY api/catalog.py api/models.py ./api/
COPY worker ./worker
COPY agent.py .
RUN python agent.py download-files
RUN useradd --create-home worker && mkdir -p /app/data && chown -R worker:worker /app
USER worker
CMD ["python", "agent.py", "start"]
