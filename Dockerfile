FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY contract_tester ./contract_tester
ENV PORT=8000
CMD ["sh", "-c", "uvicorn contract_tester.server:app --host 0.0.0.0 --port ${PORT}"]
