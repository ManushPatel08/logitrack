FROM python:3.10-slim
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy all backend code into the container
COPY . .

COPY ../worker/seed_database.py .
COPY ../worker/mock_data.py .

# Run the API server using Uvicorn
# --host 0.0.0.0 makes it accessible from outside the container
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
CMD sh -c "python seed_database.py && uvicorn main:app --host 0.0.0.0 --port 8000"