FROM python:3.10-slim
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the Streamlit app code
COPY app.py .

# Expose the port Streamlit runs on (default 8501)
EXPOSE 8501

# Command to run the Streamlit app
# --server.address 0.0.0.0 makes it accessible outside the container
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]