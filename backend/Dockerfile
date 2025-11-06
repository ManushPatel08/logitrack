FROM python:3.10-slim
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy all backend code into the container
COPY . .

# Expose default port (Cloud Run will set PORT env var). Default to 8080.
ENV PORT=8080

# Run the API server using Uvicorn. Use sh -c so we can expand $PORT at runtime.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --reload"]