FROM python:3.12-slim
RUN pip install --no-cache-dir fastapi uvicorn
RUN useradd -m app && mkdir /logs && chown app /logs
WORKDIR /app
COPY main.py .
USER app
ENV LOG_FILE=/logs/ollama.json
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "11434", "--no-server-header"]