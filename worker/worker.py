import psycopg2
import os
import time
import random
import requests

# --- DB Config ---
DB_NAME = os.environ.get("POSTGRES_DB")
DB_USER = os.environ.get("POSTGRES_USER")
DB_PASS = os.environ.get("POSTGRES_PASSWORD")
DB_HOST = "db"

# --- AI Config ---
API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
API_KEY = os.environ.get("HF_API_KEY")
headers = {"Authorization": f"Bearer {API_KEY}"}

def get_db_connection():
    conn = None
    while not conn:
        try:
            conn = psycopg2.connect(
                dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port="5432"
            )
            print("Database connection successful!")
            return conn
        except Exception as e:
            print(f"Database connection error: {e}. Retrying in 5s...")
            time.sleep(5)

def generate_mock_event():
    """Generate mock events with geographic coordinates"""
    events = [
        {
            "status": "Vessel delayed at port due to congestion.",
            "location": "Port of Singapore",
            "lat": 1.2897,
            "lon": 103.8501
        },
        {
            "status": "On time, arrived at sorting facility.",
            "location": "Los Angeles, CA",
            "lat": 34.0522,
            "lon": -118.2437
        },
        {
            "status": "Customs hold - incomplete paperwork.",
            "location": "Newark, NJ",
            "lat": 40.7357,
            "lon": -74.1724
        },
        {
            "status": "Departed from origin port.",
            "location": "Hamburg, Germany",
            "lat": 53.5511,
            "lon": 9.9937
        },
        {
            "status": "Weather delay - typhoon.",
            "location": "Shanghai, China",
            "lat": 31.2304,
            "lon": 121.4737
        },
        {
            "status": "Trucking to final destination.",
            "location": "Chicago, IL",
            "lat": 41.8781,
            "lon": -87.6298
        },
        {
            "status": "Package delivered successfully.",
            "location": "New York, USA",
            "lat": 40.7128,
            "lon": -74.0060
        }
    ]
    
    event = random.choice(events)
    return event["status"], event["location"], event["lat"], event["lon"]

# --- AI Query Function ---
def query_model(raw_text):
    if not API_KEY:
        print("Error: HF_API_KEY not set.")
        return "Error", "No API Key"

    candidate_labels = ["On Time", "Delayed", "Customs Issue", "Weather Delay", "Port Congestion", "Delivered"]

    response = requests.post(API_URL, headers=headers, json={
        "inputs": raw_text,
        "parameters": {"candidate_labels": candidate_labels}
    })

    if response.status_code == 200:
        data = response.json()
        ai_status = data['labels'][0]

        ai_reason = "N/A"
        if ai_status in ["Customs Issue", "Weather Delay", "Port Congestion"]:
            ai_reason = ai_status
            ai_status = "Delayed"
        elif ai_status == "On Time" or ai_status == "Delivered":
            ai_reason = "N/A"

        print(f"AI Result: '{raw_text}' -> Status: {ai_status}, Reason: {ai_reason}")
        return ai_status, ai_reason
    else:
        print(f"AI API Error: {response.json()}")
        if "is currently loading" in response.text:
            time.sleep(10)
            return "Retry", "Model Loading"
        return "Error", response.json().get('error', 'API Error')

# --- AI Processing Job ---
def process_ai_events(cursor):
    print("Checking for events to process with AI...")
    cursor.execute("SELECT id, raw_status_text FROM shipment_events WHERE ai_status IS NULL;")
    events_to_process = cursor.fetchall()

    if not events_to_process:
        print("No new events to process.")
        return

    print(f"Found {len(events_to_process)} events to process.")
    for event in events_to_process:
        event_id, raw_text = event
        ai_status, ai_reason = query_model(raw_text)

        if ai_status not in ["Error", "Retry"]:
            cursor.execute(
                """
                UPDATE shipment_events
                SET ai_status = %s, ai_reason = %s
                WHERE id = %s
                """,
                (ai_status, ai_reason, event_id)
            )

# --- Data Ingestion Job ---
def ingest_new_events(cursor):
    print("Checking for new data to ingest...")
    cursor.execute("SELECT id FROM shipments;")
    shipment_rows = cursor.fetchall()

    if not shipment_rows:
        print("No shipments found in database. Adding a mock one.")
        cursor.execute(
            "INSERT INTO shipments (tracking_id, origin, destination) VALUES (%s, %s, %s) RETURNING id;",
            ('TRK1Z3', 'Shanghai, China', 'New York, USA')
        )
        shipment_id = cursor.fetchone()[0]
        shipment_rows = [(shipment_id,)]

    for row in shipment_rows:
        shipment_id = row[0]
        raw_text, location, lat, lon = generate_mock_event()
        print(f"Adding event for shipment {shipment_id}: '{raw_text}' at {location} ({lat}, {lon})")
        cursor.execute(
            "INSERT INTO shipment_events (shipment_id, location, raw_status_text, latitude, longitude) VALUES (%s, %s, %s, %s, %s)",
            (shipment_id, location, raw_text, lat, lon)
        )

# --- Main Function ---
def main():
    print("Worker job starting...")
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Add new "raw" data
    ingest_new_events(cursor)

    # 2. Process "raw" data with AI
    process_ai_events(cursor)

    # 3. Commit all changes
    conn.commit()
    cursor.close()
    conn.close()
    print("Worker job finished.")

if __name__ == "__main__":
    main()