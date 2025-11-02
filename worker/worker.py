import psycopg2
import os
import time
import random
import requests
from datetime import datetime
from dotenv import load_dotenv
import json
try:
    from websocket import create_connection
except Exception:
    create_connection = None

# --- NEW: Import all pre-processed mock data ---
# Ensure your data file is named mock_data.py in the worker folder
from mock_data import ALL_MOCK_EVENTS

# Load environment variables from a local .env if present (useful for local dev)
load_dotenv()

# --- DB Config ---
DB_NAME = os.environ.get("POSTGRES_DB")
DB_USER = os.environ.get("POSTGRES_USER")
DB_PASS = os.environ.get("POSTGRES_PASSWORD")
DB_HOST = "db"

# --- API Mode Flags ---
# NOTE: We now default to AISStream when enabled; mock data is used otherwise.
USE_AIS_API = os.environ.get("USE_AIS_API", "false").lower() == "true"
DISABLE_MOCK_INGEST = os.environ.get("DISABLE_MOCK_INGEST", "false").lower() == "true"

# --- AISStream API Config ---
# Provide either a templated HTTP URL or a WebSocket URL via env. For HTTP polling,
# set AISSTREAM_REQUEST_TEMPLATE (must include {mmsi}). Example:
#   AISSTREAM_REQUEST_TEMPLATE=https://api.your-aisstream.example/v1/positions?mmsi={mmsi}
# If your provider requires an API key, set AISSTREAM_API_KEY and optionally
# AISSTREAM_AUTH_HEADER (default 'x-api-key').
AISSTREAM_REQUEST_TEMPLATE = os.environ.get("AISSTREAM_REQUEST_TEMPLATE", "")
AISSTREAM_API_KEY = os.environ.get("AISSTREAM_API_KEY", "")
AISSTREAM_AUTH_HEADER = os.environ.get("AISSTREAM_AUTH_HEADER", "x-api-key")
AIS_MMSI_LIST = [m.strip() for m in os.environ.get("AIS_MMSI_LIST", "").split(",") if m.strip()]

# AISStream mode selector: 'http' or 'ws'
AISSTREAM_MODE = os.environ.get("AISSTREAM_MODE", "http").lower()
AISSTREAM_WS_URL = os.environ.get("AISSTREAM_WS_URL", "wss://stream.aisstream.io/v0/stream")
AISSTREAM_WS_API_KEY = os.environ.get("AISSTREAM_WS_API_KEY", "")
# AISStream subscription fields
AISSTREAM_WS_BOUNDING_BOXES = os.environ.get(
    "AISSTREAM_WS_BOUNDING_BOXES",
    "[[[-90, -180], [90, 180]]]"  # whole world
)
AISSTREAM_FILTER_MESSAGE_TYPES = os.environ.get(
    "AISSTREAM_FILTER_MESSAGE_TYPES",
    "PositionReport"
)
# Optional: provide full subscribe JSON via env; if set, we will send it verbatim
AISSTREAM_WS_SUBSCRIBE_JSON = os.environ.get("AISSTREAM_WS_SUBSCRIBE_JSON", "")
AISSTREAM_WS_RECEIVE_SECONDS = int(os.environ.get("AISSTREAM_WS_RECEIVE_SECONDS", "30"))


# --- AI Config (Still needed for REAL API) ---
# Hugging Face Inference endpoint (text2text model for paraphrasing)
AI_API_URL = os.environ.get(
    "AI_API_URL",
    "https://api-inference.huggingface.co/models/google/flan-t5-base"
)
HF_API_KEY = os.environ.get("HF_API_KEY")
ai_headers = {
    "Authorization": f"Bearer {HF_API_KEY}" if HF_API_KEY else "",
    "Accept": "application/json",
    "Content-Type": "application/json",
}
AI_FALLBACK_HEURISTICS = (os.environ.get("AI_FALLBACK_HEURISTICS", "true").lower() == "true")
AI_HEURISTIC_ON_INSERT = (os.environ.get("AI_HEURISTIC_ON_INSERT", "true").lower() == "true")
AI_BACKFILL_HEURISTICS_ON_START = (os.environ.get("AI_BACKFILL_HEURISTICS_ON_START", "true").lower() == "true")
AI_BACKFILL_LIMIT = int(os.environ.get("AI_BACKFILL_LIMIT", "1000"))

# Stationary/dwell detection to flag potential delays without external context
DUPLICATE_SUPPRESS_MINUTES = int(os.environ.get("DUPLICATE_SUPPRESS_MINUTES", "10"))
STATIONARY_DELAY_MINUTES = int(os.environ.get("STATIONARY_DELAY_MINUTES", "90"))
STATIONARY_SPEED_KNOTS = float(os.environ.get("STATIONARY_SPEED_KNOTS", "0.5"))
STATIONARY_DISTANCE_EPSILON = float(os.environ.get("STATIONARY_DISTANCE_EPSILON", "0.002"))  # ~200m


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


# ==================== AI PROCESSING (HuggingFace) ====================

def _categorize_from_nav_desc(text: str) -> str:
    """Map nav status description into a coarse category for KPIs.
    This keeps /at_risk and KPI endpoints meaningful while we show paraphrases.
    """
    t = (text or "").lower()
    delayed_signals = [
        "anchor", "moored", "aground", "restricted", "not under command",
        "constrained", "sart", "search and rescue"
    ]
    if any(k in t for k in delayed_signals):
        return "Delayed"
    return "On Time"


def query_model(raw_text):
    if not HF_API_KEY:
        print("HF_API_KEY not set; using heuristics if enabled.")
        if AI_FALLBACK_HEURISTICS:
            return heuristic_classify(raw_text)
        return "Error", "No API Key"

    try:
        response = requests.post(
            AI_API_URL,
            headers=ai_headers,
            json={
                "inputs": f"Paraphrase this navigational status in a user-friendly way: {raw_text}",
                "parameters": {"max_length": 50, "do_sample": True, "temperature": 0.7}
            },
            timeout=30,
        )
    except Exception as e:
        print(f"AI API Error: request failed: {e}")
        if AI_FALLBACK_HEURISTICS:
            return heuristic_classify(raw_text)
        return "Error", "Request failed"

    if response.status_code == 200:
        try:
            data = response.json()
        except Exception:
            print(f"AI API Error: non-JSON success response: status {response.status_code}, body: {response.text[:200]}")
            if AI_FALLBACK_HEURISTICS:
                return heuristic_classify(raw_text)
            return "Error", "Non-JSON response"
        
        # For text generation, data is list of dicts with 'generated_text'
        if isinstance(data, list) and data:
            generated = data[0].get('generated_text', raw_text)
            # Clean up: remove the prompt if present
            if generated.startswith(f"Paraphrase this navigational status in a user-friendly way: {raw_text}"):
                generated = generated[len(f"Paraphrase this navigational status in a user-friendly way: {raw_text}"):].strip()
            print(f"AI Paraphrase: '{raw_text}' -> '{generated}'")
            # Keep categorical status for KPIs, store paraphrase in ai_reason
            category = _categorize_from_nav_desc(raw_text)
            return category, generated
        else:
            print(f"AI API Error: unexpected response format: {data}")
            if AI_FALLBACK_HEURISTICS:
                return heuristic_classify(raw_text)
            return "Error", "Unexpected format"
    else:
        # Gracefully handle non-JSON errors
        err_body = None
        try:
            err_body = response.json()
        except Exception:
            err_body = {"error": response.text[:200]}
        print(f"AI API Error: status {response.status_code} body: {err_body}")
        if "is currently loading" in response.text:
            time.sleep(10)
            return "Retry", "Model Loading"
        if AI_FALLBACK_HEURISTICS:
            return heuristic_classify(raw_text)
        return "Error", (err_body.get('error') if isinstance(err_body, dict) else 'API Error')

def heuristic_classify(raw_text: str):
    """Very simple keyword-based fallback classification."""
    t = (raw_text or "").lower()
    if any(k in t for k in ["delivered", "pod "]):
        return "Delivered", "N/A"
    if any(k in t for k in ["port congestion", "berth", "berthing", "queue", "anchorage"]):
        return "Delayed", "Port Congestion"
    if "customs" in t:
        return "Delayed", "Customs Issue"
    if any(k in t for k in ["weather", "storm", "cyclone", "hurricane", "winds", "typhoon"]):
        return "Delayed", "Weather Delay"
    if "delay" in t:
        return "Delayed", "N/A"
    return "On Time", "N/A"

def process_ai_events(cursor):
    """Checks DB for events needing AI processing (paraphrase nav status)."""
    if not HF_API_KEY:
        print("HF_API_KEY is not set; skipping AI processing this cycle.")
        return
    print("Checking for events to process with AI...")
    # Process items where ai_status is NULL (new) or ai_reason is NULL (paraphrase missing)
    cursor.execute("SELECT id, raw_status_text FROM shipment_events WHERE ai_status IS NULL OR ai_reason IS NULL;")
    events_to_process = cursor.fetchall()

    if not events_to_process:
        print("No new events to process.")
        return

    max_per_cycle = int(os.environ.get("AI_MAX_PER_CYCLE", "5"))
    if len(events_to_process) > max_per_cycle:
        print(f"Found {len(events_to_process)} events to process. Limiting to {max_per_cycle} this cycle.")
    else:
        print(f"Found {len(events_to_process)} events to process.")
    for event in events_to_process[:max_per_cycle]:
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

def backfill_null_ai_events(cursor, limit=1000):
    """Fill ai_status/ai_reason heuristically for existing events with NULL ai_status.
    Helps remove 'Unknown' in UI without waiting for HF API.
    """
    cursor.execute("SELECT id, raw_status_text FROM shipment_events WHERE ai_status IS NULL LIMIT %s;", (limit,))
    rows = cursor.fetchall()
    if not rows:
        return 0
    count = 0
    for event_id, raw_text in rows:
        s, r = heuristic_classify(raw_text)
        cursor.execute(
            "UPDATE shipment_events SET ai_status=%s, ai_reason=%s WHERE id=%s",
            (s, r, event_id)
        )
        count += 1
    print(f"AI Backfill: heuristically labeled {count} events.")
    return count

# ==================== DATA INGESTION ====================

def parse_ais_item(item):
    """Best-effort parser for AIS item structures into our common dict.
    Expects keys like mmsi, lat/latitude, lon/longitude, sog/speed, cog/course, nav_status/status, timestamp/name.
    """
    def g(*keys, default=None):
        for k in keys:
            if k in item and item[k] not in (None, ""):
                return item[k]
        return default

    mmsi = str(g("mmsi", "MMSI", default="unknown"))
    name = g("name", "shipname", "vessel_name", default=f"Vessel {mmsi}")
    lat = float(g("lat", "latitude", "LAT", default=0) or 0)
    lon = float(g("lon", "lng", "longitude", "LON", default=0) or 0)
    speed = float(g("sog", "speed", "SPEED", default=0) or 0)
    course = g("cog", "course", "COURSE", default=0)
    status = g("nav_status", "status", "STATUS", default="Unknown")
    dest = g("destination", "DESTINATION", default="Unknown")
    ts = g("timestamp", "TIMESTAMP", default=datetime.utcnow().isoformat())

    # Human text - make it more descriptive for better AI classification
    nav_status_desc = {
        0: "Under way using engine",
        1: "At anchor",
        2: "Not under command",
        3: "Restricted maneuverability",
        4: "Constrained by draught",
        5: "Moored",
        6: "Aground",
        7: "Engaged in fishing",
        8: "Under way sailing",
        9: "Reserved for future use",
        10: "Reserved for future use",
        11: "Power-driven vessel towing astern",
        12: "Power-driven vessel pushing ahead or towing alongside",
        13: "Reserved for future use",
        14: "AIS-SART (Search and Rescue Transmitter)",
        15: "Undefined"
    }.get(status, "Unknown status")

    # For AI paraphrasing we want to pass the pure nav status description
    status_text = nav_status_desc

    return {
        "mmsi": mmsi,
        "vessel_name": name,
        "latitude": lat,
        "longitude": lon,
        "speed": speed,
        "course": course,
        "destination": dest,
        "status": status,
        "timestamp": ts,
        "status_text": status_text,
    }

def ingest_aisstream_data(cursor):
    """Fetch vessel tracking data from AISStream-compatible HTTP endpoint.
    Requires AISSTREAM_REQUEST_TEMPLATE to be set and contain {mmsi} placeholder.
    MMSIs come from AIS_MMSI_LIST (env). If empty, we skip gracefully.
    """
    if not AISSTREAM_REQUEST_TEMPLATE or "{mmsi}" not in AISSTREAM_REQUEST_TEMPLATE:
        print("AISStream: AISSTREAM_REQUEST_TEMPLATE is not configured or missing {mmsi} placeholder. Skipping.")
        return

    if not AIS_MMSI_LIST:
        print("AISStream: AIS_MMSI_LIST is empty. Set comma-separated MMSIs in env to track.")
        return

    headers = {}
    if AISSTREAM_API_KEY:
        headers[AISSTREAM_AUTH_HEADER] = AISSTREAM_API_KEY

    for mmsi in AIS_MMSI_LIST:
        url = AISSTREAM_REQUEST_TEMPLATE.format(mmsi=mmsi)
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                print(f"AISStream: HTTP {r.status_code} for {mmsi} - {r.text[:200]}")
                continue
            data = r.json()

            # Normalize: data may be a list or dict with 'positions' key
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                if "positions" in data and isinstance(data["positions"], list):
                    items = data["positions"]
                else:
                    items = [data]

            if not items:
                print(f"AISStream: no positions for {mmsi}")
                continue

            # Upsert shipment once per MMSI
            # Origin/destination unknown from AIS; store generic placeholders
            shipment_id = upsert_shipment(cursor, mmsi, origin="Unknown", destination="Unknown")

            # Take the most recent item (assume last or pick max by timestamp)
            latest = items[-1]
            parsed = parse_ais_item(latest)

            # Avoid duplicate noise in short intervals
            cursor.execute(
                f"""
                SELECT id FROM shipment_events
                WHERE shipment_id = %s
                  AND latitude = %s AND longitude = %s
                  AND timestamp > NOW() - INTERVAL '{DUPLICATE_SUPPRESS_MINUTES} minutes'
                """,
                (shipment_id, parsed["latitude"], parsed["longitude"]) 
            )
            if cursor.fetchone():
                print(f"AISStream: ‹-› No significant movement for vessel {mmsi}")
                continue

            location = f"{parsed['vessel_name']} - Lat: {parsed['latitude']:.4f}, Lon: {parsed['longitude']:.4f}"
            # Heuristic AI on insert to avoid Unknowns in UI
            ai_status, ai_reason = (None, None)
            if AI_HEURISTIC_ON_INSERT:
                # Dwell-based heuristic: if essentially stopped and stayed near same spot long enough → mark Delayed
                try:
                    cursor.execute(
                        """
                        SELECT timestamp, latitude, longitude
                        FROM shipment_events
                        WHERE shipment_id = %s
                        ORDER BY timestamp DESC
                        LIMIT 1
                        """,
                        (shipment_id,)
                    )
                    last = cursor.fetchone()
                except Exception:
                    last = None

                if last is not None:
                    last_ts, last_lat, last_lon = last
                    # Compute simple distance threshold in degrees
                    dlat = abs((last_lat or 0) - parsed["latitude"])
                    dlon = abs((last_lon or 0) - parsed["longitude"])
                    dwell = (datetime.utcnow() - last_ts).total_seconds() / 60.0 if last_ts else 0
                else:
                    dlat = dlon = dwell = 0

                if (parsed["speed"] <= STATIONARY_SPEED_KNOTS and
                    dlat < STATIONARY_DISTANCE_EPSILON and dlon < STATIONARY_DISTANCE_EPSILON and
                    dwell >= STATIONARY_DELAY_MINUTES):
                    ai_status, ai_reason = ("Delayed", "Port Congestion")
                else:
                    ai_status, ai_reason = heuristic_classify(parsed["status_text"])
            cursor.execute(
                """
                INSERT INTO shipment_events
                (shipment_id, timestamp, location, raw_status_text, latitude, longitude, ai_status, ai_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    shipment_id,
                    parsed["timestamp"],
                    location,
                    parsed["status_text"],
                    parsed["latitude"],
                    parsed["longitude"],
                    ai_status,
                    ai_reason,
                )
            )
            print(f"✓ AISStream updated {mmsi}: {parsed['status_text']}")
        except Exception as e:
            print(f"AISStream: error for {mmsi}: {e}")

def _parse_bounding_boxes():
    try:
        boxes = json.loads(AISSTREAM_WS_BOUNDING_BOXES)
        if isinstance(boxes, list) and boxes:
            return boxes
    except Exception:
        pass
    # default world
    return [[[-90, -180], [90, 180]]]

def _parse_filter_message_types():
    # allow JSON list or comma-separated
    raw = AISSTREAM_FILTER_MESSAGE_TYPES.strip()
    if not raw:
        return []
    try:
        val = json.loads(raw)
        if isinstance(val, list):
            return [str(x) for x in val]
    except Exception:
        pass
    return [s.strip() for s in raw.split(',') if s.strip()]

def _ws_build_subscribe_message():
    # If provided, honor raw JSON from env
    if AISSTREAM_WS_SUBSCRIBE_JSON:
        try:
            return json.loads(AISSTREAM_WS_SUBSCRIBE_JSON)
        except Exception as e:
            print(f"AISStream WS: invalid AISSTREAM_WS_SUBSCRIBE_JSON: {e}")

    msg = {
        "APIKey": AISSTREAM_WS_API_KEY,
        "BoundingBoxes": _parse_bounding_boxes(),
    }
    if AIS_MMSI_LIST:
        # Max 50 MMSIs recommended by docs
        msg["FiltersShipMMSI"] = AIS_MMSI_LIST[:50]
    fmts = _parse_filter_message_types()
    if fmts:
        msg["FilterMessageTypes"] = fmts
    return msg

def _ws_extract_payload(msg):
    """Extract AISStream.io payload and normalize to fields used by parse_ais_item().

    AISStream format example:
    {
      "MessageType": "PositionReport",
      "Metadata": {"MMSI": 259000420, "ShipName":"...", "latitude": 66.02, "longitude": 12.25, ...},
      "Message": {"PositionReport": {"UserID": 259000420, "Latitude": 66.02, "Longitude": 12.25, ...}}
    }
    """
    try:
        # Handle bytes payloads from websocket-client
        if isinstance(msg, (bytes, bytearray)):
            msg = msg.decode("utf-8", "ignore")
        if isinstance(msg, str):
            msg = json.loads(msg)
    except Exception:
        return None

    if not isinstance(msg, dict):
        return None

    # Prefer inner PositionReport if present
    inner = None
    message_block = msg.get("Message") or msg.get("message")
    if isinstance(message_block, dict):
        # Try to locate the inner object by message type
        mt = msg.get("MessageType") or msg.get("messageType")
        if mt and isinstance(message_block.get(mt), dict):
            inner = message_block.get(mt)
        # Fallback to any dict inside
        if inner is None:
            for v in message_block.values():
                if isinstance(v, dict):
                    inner = v
                    break

    metadata = msg.get("MetaData") or msg.get("Metadata") or {}

    # Build a normalized dict
    norm = {}
    # MMSI/UserID
    mmsi = None
    if isinstance(inner, dict):
        mmsi = inner.get("UserID") or inner.get("MMSI")
    if mmsi is None:
        mmsi = metadata.get("MMSI")
    if mmsi is not None:
        norm["mmsi"] = str(mmsi)

    # Latitude/Longitude: try inner first, then metadata; accept various casings
    def pick(obj, *keys):
        for k in keys:
            if isinstance(obj, dict) and k in obj and obj[k] is not None:
                return obj[k]
        return None

    lat = None
    lon = None
    if isinstance(inner, dict):
        lat = pick(inner, "Latitude", "latitude", "LAT", "lat")
        lon = pick(inner, "Longitude", "longitude", "LON", "lon")
    if lat is None or lon is None:
        lat = lat if lat is not None else pick(metadata, "Latitude", "latitude")
        lon = lon if lon is not None else pick(metadata, "Longitude", "longitude")
    if lat is not None and lon is not None:
        norm["latitude"] = float(lat)
        norm["longitude"] = float(lon)

    # Optional fields
    ship_name = pick(metadata, "ShipName", "ship_name", "name")
    if ship_name:
        norm["vessel_name"] = ship_name
    # NavigationalStatus from inner message
    if isinstance(inner, dict):
        nav_status = inner.get("NavigationalStatus")
        if nav_status is not None:
            norm["nav_status"] = int(nav_status)
    # Timestamp if present
    ts = pick(metadata, "time_utc", "timestamp")
    if ts is not None:
        try:
            # Accept numeric epoch seconds
            if isinstance(ts, (int, float)):
                norm["timestamp"] = datetime.utcfromtimestamp(float(ts)).isoformat()
            else:
                ts_str = str(ts)
                # Only accept ISO-like strings (contain 'T'); otherwise let default be applied later
                if "T" in ts_str:
                    norm["timestamp"] = ts_str
        except Exception:
            # Ignore malformed ts; parse_ais_item will default to now
            pass

    # If we found lat/lon and mmsi, return
    if "latitude" in norm and "longitude" in norm:
        return norm

    # Fallbacks: accept objects that already have lat/lon keys
    if any(k in msg for k in ("lat", "latitude", "LAT")):
        return msg
    if isinstance(inner, dict) and any(k in inner for k in ("lat", "latitude", "LAT")):
        return inner
    return None

def _ws_extract_destination(msg):
    """Extract MMSI and Destination from ShipStaticData/StaticDataReport messages."""
    try:
        if isinstance(msg, (bytes, bytearray)):
            msg = msg.decode("utf-8", "ignore")
        if isinstance(msg, str):
            msg = json.loads(msg)
        if not isinstance(msg, dict):
            return None, None
        message_block = msg.get("Message") or msg.get("message") or {}
        # Try both keys commonly used by AISStream
        static = message_block.get("ShipStaticData") or message_block.get("StaticDataReport")
        if not isinstance(static, dict):
            return None, None
        dest = static.get("Destination") or static.get("destination")
        # MMSI can be inside static (UserID) or metadata
        mmsi = static.get("UserID")
        if mmsi is None:
            meta = msg.get("MetaData") or msg.get("Metadata") or {}
            mmsi = meta.get("MMSI")
        return (str(mmsi) if mmsi is not None else None), (dest.strip() if isinstance(dest, str) else None)
    except Exception:
        return None, None

def ingest_aisstream_ws(cursor, receive_seconds=30):
    if create_connection is None:
        print("AISStream WS: websocket-client not installed. Add 'websocket-client' to worker/requirements.txt")
        return
    if not AISSTREAM_WS_URL:
        print("AISStream WS: AISSTREAM_WS_URL not set. Skipping.")
        return
    # Ensure API key is present unless full subscribe JSON is provided
    if not AISSTREAM_WS_API_KEY and not AISSTREAM_WS_SUBSCRIBE_JSON:
        print("AISStream WS: APIKey missing. Set AISSTREAM_WS_API_KEY in your environment.")
        return

    # Per AISStream docs: connect to wss endpoint and send subscription with APIKey & BoundingBoxes
    url = AISSTREAM_WS_URL
    print(f"AISStream WS: connecting to {url}")
    try:
        ws = create_connection(url, timeout=10)
    except Exception as e:
        print(f"AISStream WS: connection error: {e}")
        return

    # Send subscribe message (must be within 3 seconds)
    sub_msg = _ws_build_subscribe_message()
    if not sub_msg.get("APIKey"):
        print("AISStream WS: APIKey missing in subscribe message.")
    try:
        # Mask API key in logs
        log_msg = dict(sub_msg)
        if "APIKey" in log_msg:
            log_msg["APIKey"] = "***MASKED***"
        ws.send(json.dumps(sub_msg))
        print(f"AISStream WS: subscribe sent with payload: {json.dumps(log_msg)}")
    except Exception as e:
        print(f"AISStream WS: subscribe send error: {e}")

    # Receive for a limited time per loop iteration
    ws.settimeout(5)
    end_ts = time.time() + max(5, int(receive_seconds))
    count = 0
    non_position_logs = 0
    while time.time() < end_ts:
        try:
            msg = ws.recv()
        except Exception:
            # brief idle
            time.sleep(0.2)
            continue

        payload = _ws_extract_payload(msg)
        if not payload:
            # Try to update destination from static data
            mmsi, dest = _ws_extract_destination(msg)
            if mmsi and dest:
                try:
                    cursor.execute(
                        "UPDATE shipments SET destination = %s WHERE tracking_id = %s",
                        (dest, mmsi)
                    )
                    print(f"Updated destination for {mmsi} -> {dest}")
                except Exception as e:
                    print(f"Failed to update destination for {mmsi}: {e}")
            else:
                # Log a few non-position messages for diagnostics
                if non_position_logs < 5:
                    try:
                        preview = msg if isinstance(msg, str) else json.dumps(msg)[:300]
                    except Exception:
                        preview = str(msg)[:300]
                    print(f"AISStream WS: non-position message: {preview}")
                    non_position_logs += 1
            continue
        parsed = parse_ais_item(payload)
        mmsi = parsed.get("mmsi", "unknown")
        shipment_id = upsert_shipment(cursor, mmsi, origin="Unknown", destination="Unknown")

        # Duplicate suppression (1 hour, same lat/lon)
        cursor.execute(
            "SELECT id FROM shipment_events WHERE shipment_id = %s AND latitude = %s AND longitude = %s AND timestamp > NOW() - INTERVAL '1 hour'",
            (shipment_id, parsed["latitude"], parsed["longitude"])
        )
        if cursor.fetchone():
            continue

        location = f"{parsed['vessel_name']} - Lat: {parsed['latitude']:.4f}, Lon: {parsed['longitude']:.4f}"
        # Set categorical status immediately to avoid Unknowns in UI; leave reason for paraphraser
        ai_status, ai_reason = (_categorize_from_nav_desc(parsed["status_text"]), None)
        cursor.execute(
            """
            INSERT INTO shipment_events
            (shipment_id, timestamp, location, raw_status_text, latitude, longitude, ai_status, ai_reason)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                shipment_id,
                datetime.utcnow().isoformat(),
                location,
                parsed["status_text"],
                parsed["latitude"],
                parsed["longitude"],
                ai_status,
                ai_reason,
            )
        )
        count += 1
    try:
        ws.close()
    except Exception:
        pass
    print(f"AISStream WS: ingested {count} events in this cycle")
    if count == 0:
        print("AISStream WS: Received 0 events. Tips: (1) Increase AISSTREAM_WS_RECEIVE_SECONDS, (2) remove FilterMessageTypes, (3) narrow BoundingBoxes to a busy region like Singapore or English Channel, (4) verify API key plan supports WS.")

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


def ingest_mock_events(cursor):
    """
    Ingest a random event from the mock_data list *to be processed*.
    """
    print("🎲 Using MOCK data (set USE_AIS_API=true to use AISStream)...")

    # Pick one random event from our big list
    event = random.choice(ALL_MOCK_EVENTS)

    # Get or create the shipment using the pre-defined O/D
    shipment_id = upsert_shipment(
        cursor,
        event["shipid"],
        event["origin"],
        event["destination"]
    )

    print(f"Adding mock event for {event['shipid']} to be processed by AI.")

    # Insert the event with immediate categorical status to avoid Unknowns in UI
    # Leave ai_reason as NULL so the AI paraphraser can fill it later
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
            _categorize_from_nav_desc(event["raw_status_text"]),
            None
        )
    )

# ==================== MAIN ====================

def main():
    print("=" * 60)
    print("Worker job starting...")
    mode = 'AISSTREAM' if USE_AIS_API else 'MOCK'
    print(f"Mode: {mode}")
    print("=" * 60)

    conn = get_db_connection()
    cursor = conn.cursor()

    if USE_AIS_API:
        if AISSTREAM_MODE == 'ws':
            ingest_aisstream_ws(cursor, receive_seconds=AISSTREAM_WS_RECEIVE_SECONDS)
        else:
            ingest_aisstream_data(cursor)
    else:
        # Optionally disable mock ingestion entirely
        if DISABLE_MOCK_INGEST:
            print("🔇 Mock ingestion disabled (DISABLE_MOCK_INGEST=true). Skipping event insert this cycle.")
        else:
            # Mock data is now ingested *without* AI fields
            ingest_mock_events(cursor)

    # Heuristic backfill to reduce 'Unknown' reasons for existing rows
    if AI_BACKFILL_HEURISTICS_ON_START:
        backfill_null_ai_events(cursor, limit=AI_BACKFILL_LIMIT)

    # Always run AI processing, regardless of mode.
    # This will process mock data (if USE_REAL_API=false)
    # or real data (if USE_REAL_API=true).
    process_ai_events(cursor)

    conn.commit()
    cursor.close()
    conn.close()
    print("Worker job finished.")
    print("=" * 60)

if __name__ == "__main__":
    print("Worker starting in continuous mode...")
    if USE_AIS_API:
        print("API Mode: AISStream (Real Ships)")
        if AISSTREAM_MODE == 'ws':
            interval = int(os.environ.get("AISSTREAM_POLL_INTERVAL_SECONDS", "60"))
            print(f"Transport: WebSocket | receive window: {AISSTREAM_WS_RECEIVE_SECONDS}s | cycle interval: {interval}s")
        else:
            interval = int(os.environ.get("AISSTREAM_POLL_INTERVAL_SECONDS", "60"))
            print(f"Transport: HTTP polling | interval: {interval}s")
    else:
        print("API Mode: Mock Data")
        print(f"Using {len(ALL_MOCK_EVENTS)} pre-processed mock events.")
        interval = int(os.environ.get("MOCK_EVENT_INTERVAL_SECONDS", "5"))

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