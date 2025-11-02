# worker/seed_database.py

import psycopg2
import os
import time
from datetime import datetime

# Import the data we want to load
from mock_data import ALL_MOCK_EVENTS

# --- DB Config (Copied from worker.py) ---
DB_NAME = os.environ.get("POSTGRES_DB")
DB_USER = os.environ.get("POSTGRES_USER")
DB_PASS = os.environ.get("POSTGRES_PASSWORD")
DB_HOST = os.environ.get("POSTGRES_HOST")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")

def get_db_connection():
    """Helper function to connect to the DB."""
    conn = None
    while not conn:
        try:
            conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                host=DB_HOST,
                port=DB_PORT,
            )
            print("Database connection successful!")
            return conn
        except Exception as e:
            print(f"Database connection error: {e}. Retrying in 5s...")
            time.sleep(5)

def upsert_shipment(cursor, tracking_id, origin="Unknown", destination="Unknown"):
    """Finds or creates a shipment and returns its ID."""
    cursor.execute('SELECT id FROM shipments WHERE tracking_id = %s', (tracking_id,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    # Shipment doesn't exist, create it
    cursor.execute('INSERT INTO shipments (tracking_id, origin, destination) VALUES (%s, %s, %s) RETURNING id',
                   (tracking_id, origin, destination))
    return cursor.fetchone()[0]

def main():
    print("=" * 60)
    print(f"Starting database seeding... loading {len(ALL_MOCK_EVENTS)} events.")
    print("=" * 60)

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Clear all existing data from the tables
    print("Clearing old data (TRUNCATE)...")
    cursor.execute("TRUNCATE TABLE shipment_events, shipments RESTART IDENTITY;")

    # 2. Loop and insert EVERY event from the list
    count = 0
    for event in ALL_MOCK_EVENTS:
        try:
            # Get or create the shipment
            shipment_id = upsert_shipment(
                cursor, 
                event["shipid"], 
                event["origin"], 
                event["destination"]
            )
            
            # Insert the pre-processed event
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
            count += 1
        except Exception as e:
            print(f"Error inserting event {event['shipid']}: {e}")
            conn.rollback() # Rollback this one bad event
        
    # 3. Commit all changes at the end
    conn.commit()
    cursor.close()
    conn.close()
    
    print("=" * 60)
    print(f"✅ Seeding complete! Inserted {count} total events.")
    print("=" * 60)

if __name__ == "__main__":
    main()