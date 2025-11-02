FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the script
COPY . .

# Command to run
CMD ["python", "worker.py"]