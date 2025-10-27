FROM python:3.10-slim
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the script
COPY worker.py .

# Command to run
CMD ["python", "worker.py"]