FROM python:3.10-slim
WORKDIR /app

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# Copy all backend code
COPY backend/ .

# --- FIX ---
# 1. Copy the script that GENERATES the data (it's in git)
COPY generate_mock_data.py .

# 2. Copy the script that SEEDS the data (it's in git)
COPY worker/seed_database.py .
 
# 3. RUN the generator to create the mock_data.py file
# This file will now exist inside the container at /app/mock_data.py
RUN python generate_mock_data.py > mock_data.py
# --- END FIX ---

# 4. The CMD can now run.
# seed_database.py will run and import mock_data.py
CMD sh -c "python seed_database.py && uvicorn main:app --host 0.0.0.0 --port 8000"