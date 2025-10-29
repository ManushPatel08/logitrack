import psycopg2
import os
import time
import random
import requests
from datetime import datetime

# --- NEW: Import all pre-processed mock data ---
# Ensure your data file is named mock_data.py in the worker folder
from mock_data import ALL_MOCK_EVENTS

# --- DB Config ---
DB_NAME = os.environ.get("POSTGRES_DB")
DB_USER = os.environ.get("POSTGRES_USER")
DB_PASS = os.environ.get("POSTGRES_PASSWORD")
DB_HOST = "db"

# --- MarineTraffic API Config ---
MARINETRAFFIC_API_KEY = os.environ.get("MARINETRAFFIC_API_KEY")
USE_REAL_API = os.environ.get("USE_REAL_API", "false").lower() == "true"

# --- AI Config (Still needed for REAL API) ---
AI_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
HF_API_KEY = os.environ.get("HF_API_KEY")
ai_headers = {"Authorization": f"Bearer {HF_API_KEY}"}


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

# ==================== MARINETRAFFIC API (Unchanged) ====================

# Major cargo ships (MMSI numbers)
REAL_VESSELS = [
    {"mmsi": "477567100", "name": "MSC GULSUN", "route": "China → Europe"},
    {"mmsi": "477992900", "name": "HMM ALGECIRAS", "route": "Asia → Europe"},
    {"mmsi": "477960600", "name": "EVER ACE", "route": "Asia → North America"},
    {"mmsi": "636019825", "name": "CMA CGM ANTOINE", "route": "Europe → Asia"},
    {"mmsi": "565388000", "name": "OOCL HONG KONG", "route": "Asia → Europe"},
    {"mmsi": "477358700", "name": "COSCO UNIVERSE", "route": "China → Europe"},
    {"mmsi": "209373000", "name": "MAERSK MOLLER", "route": "Europe → Asia"},
    {"mmsi": "477059500", "name": "CSCL GLOBE", "route": "Asia → Europe"},
]

def fetch_vessel_from_marinetraffic(mmsi):
    """Fetch real vessel data from MarineTraffic API"""
    if not MARINETRAFFIC_API_KEY:
        print("MarineTraffic API key not configured")
        return None

    # Using the Simple API (included in free trial)
    url = f"https://services.marinetraffic.com/api/exportvessel/v:5/{MARINETRAFFIC_API_KEY}/timespan:10/protocol:jsono/mmsi:{mmsi}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()

            if data and len(data) > 0:
                vessel = data[0]

                return {
                    "vessel_name": vessel.get("SHIPNAME", "Unknown"),
                    "latitude": float(vessel.get("LAT", 0)),
                    "longitude": float(vessel.get("LON", 0)),
                    "speed": float(vessel.get("SPEED", 0)),
                    "course": vessel.get("COURSE", 0),
                    "destination": vessel.get("DESTINATION", "Unknown"),
                    "status": vessel.get("STATUS", "Unknown"),
                    "timestamp": vessel.get("TIMESTAMP", "")
                }
        else:
            print(f"MarineTraffic API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error fetching vessel data: {e}")
        return None

def get_vessel_status_text(status, speed):
    """Convert status to human-readable text"""
    if speed == 0:
        return f"Stationary at port - {status}"
    elif speed < 5:
        return f"Slow speed ({speed} knots) - {status}"
    elif speed > 15:
        return f"High speed ({speed} knots) - {status}"
    else:
        return f"Normal transit speed ({speed} knots) - {status}"

# ==================== AI PROCESSING (For REAL API) ====================

def query_model(raw_text):
    if not HF_API_KEY:
        print("Error: HF_API_KEY not set.")
        return "Error", "No API Key"

    candidate_labels = ["On Time", "Delayed", "Customs Issue", "Weather Delay", "Port Congestion", "Delivered"]

    response = requests.post(AI_API_URL, headers=ai_headers, json={
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

def process_ai_events(cursor):
    """Checks DB for events needing AI processing (only used for REAL API data)"""
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

# ==================== DATA INGESTION ====================

def upsert_shipment(cursor, tracking_id, origin="Unknown", destination="Unknown"):
    """Finds or creates a shipment and returns its ID."""
    cursor.execute('SELECT id FROM shipments WHERE tracking_id = %s', (tracking_id,))
    row = cursor.fetchone()
    if row:
        return row[0]

    # Shipment doesn't exist, create it with the provided O/D
    cursor.execute('INSERT INTO shipments (tracking_id, origin, destination) VALUES (%s, %s, %s) RETURNING id',
                   (tracking_id, origin, destination))
    return cursor.fetchone()[0]

def ingest_real_vessel_data(cursor):
    """Fetch REAL vessel tracking data"""
    print("🚢 Fetching REAL vessel tracking data from MarineTraffic API...")

    for vessel in REAL_VESSELS:
        origin, destination = vessel["route"].split(" → ")
        # Use upsert_shipment to create if not exists
        upsert_shipment(cursor, vessel["mmsi"], origin, destination)

    cursor.execute("SELECT id, tracking_id FROM shipments;")
    shipments = cursor.fetchall()

    for shipment_id, mmsi in shipments:
        # Only process shipments that are in our REAL_VESSELS list
        if not any(v['mmsi'] == mmsi for v in REAL_VESSELS):
            continue

        vessel_data = fetch_vessel_from_marinetraffic(mmsi)

        if vessel_data:
            status_text = get_vessel_status_text(vessel_data["status"], vessel_data["speed"])
            location = f"{vessel_data['vessel_name']} - Lat: {vessel_data['latitude']:.4f}, Lon: {vessel_data['longitude']:.4f}"

            # Check if a similar event already exists recently
            cursor.execute(
                "SELECT id FROM shipment_events WHERE shipment_id = %s AND latitude = %s AND longitude = %s AND timestamp > NOW() - INTERVAL '2 hours'",
                (shipment_id, vessel_data["latitude"], vessel_data["longitude"])
            )

            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO shipment_events
                    (shipment_id, location, raw_status_text, latitude, longitude)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (shipment_id, location, status_text, vessel_data["latitude"], vessel_data["longitude"])
                )
                print(f"✓ Updated vessel {mmsi}: {status_text}")
            else:
                print(f"‹-› No significant movement for vessel {mmsi}")
        else:
            print(f"✗ Could not fetch data for vessel {mmsi}")

        time.sleep(2)  # Rate limiting - important for free tier

def ingest_mock_events(cursor):
    """
    Ingest a random pre-processed event from the mock_data list.
    """
    print("🎲 Using MOCK data (set USE_REAL_API=true to use MarineTraffic)...")

    # Pick one random event from our big list
    event = random.choice(ALL_MOCK_EVENTS)

    # Get or create the shipment using the pre-defined O/D
    shipment_id = upsert_shipment(
        cursor,
        event["shipid"],
        event["origin"],
        event["destination"]
    )

    print(f"Adding event for {event['shipid']}: (Status: {event['ai_status']}) at {event['location']}")

    # Insert the pre-processed event directly
    cursor.execute(
        """
        INSERT INTO shipment_events
        (shipment_id, timestamp, location, raw_status_text, latitude, longitude, ai_status, ai_reason)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            shipment_id,
            event["timestamp"],
            event["location"],
            event["raw_status_text"],
            event["latitude"],
            event["longitude"],
            event["ai_status"],
            event["ai_reason"]
        )
    )

# ==================== MAIN ====================

def main():
    print("=" * 60)
    print("Worker job starting...")
    print(f"Mode: {'REAL VESSEL TRACKING (MarineTraffic)' if USE_REAL_API else 'MOCK DATA'}")
    print("=" * 60)

    conn = get_db_connection()
    cursor = conn.cursor()

    if USE_REAL_API:
        ingest_real_vessel_data(cursor)
        # Only run AI processing if we're using the real API
        process_ai_events(cursor)
    else:
        # Mock data is already processed, just ingest it
        ingest_mock_events(cursor)

    conn.commit()
    cursor.close()
    conn.close()
    print("Worker job finished.")
    print("=" * 60)

if __name__ == "__main__":
    print("Worker starting in continuous mode...")
    print(f"API Mode: {'MarineTraffic (Real Ships)' if USE_REAL_API else 'Mock Data'}")

    if USE_REAL_API:
        print("Tracking REAL cargo ships worldwide!")
        print("Will update every 10 minutes (free tier rate limit).")
        interval = 600  # 10 minutes
    else:
        print("Will generate new events every 30 seconds.")
        print(f"Using {len(ALL_MOCK_EVENTS)} pre-processed mock events.")
        interval = 30

    while True:
        try:
            main()
            print(f"Sleeping for {interval} seconds...")
            time.sleep(interval)
        except KeyboardInterrupt:
            print("Worker stopped by user.")
            break
        except Exception as e:
            print(f"Error in worker loop: {e}")
            print("Retrying in 10 seconds...")
            time.sleep(10)