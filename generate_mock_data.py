import random
from datetime import datetime, timedelta

# Real-world ports and major shipping locations with coordinates
PORTS = [
    ("Shanghai, China", 31.2304, 121.4737),
    ("Singapore", 1.2897, 103.8501),
    ("Rotterdam, Netherlands", 51.9225, 4.4792),
    ("Hamburg, Germany", 53.5511, 9.9937),
    ("Los Angeles, USA", 34.0522, -118.2437),
    ("Long Beach, USA", 33.7701, -118.1937),
    ("New York, USA", 40.7128, -74.0060),
    ("Hong Kong", 22.3193, 114.1694),
    ("Busan, South Korea", 35.1796, 129.0756),
    ("Dubai, UAE", 25.2048, 55.2708),
    ("Tokyo, Japan", 35.6762, 139.6503),
    ("Mumbai, India", 19.0760, 72.8777),
    ("London, UK", 51.5074, -0.1278),
    ("Sydney, Australia", -33.8688, 151.2093),
    ("Vancouver, Canada", 49.2827, -123.1207),
    ("Seattle, USA", 47.6062, -122.3321),
    ("Miami, USA", 25.7617, -80.1918),
    ("Santos, Brazil", -23.9608, -46.3334),
    ("Buenos Aires, Argentina", -34.6037, -58.3816),
    ("Melbourne, Australia", -37.8136, 144.9631),
    ("Antwerp, Belgium", 51.2194, 4.4025),
    ("Barcelona, Spain", 41.3851, 2.1734),
    ("Istanbul, Turkey", 41.0082, 28.9784),
    ("Jeddah, Saudi Arabia", 21.5433, 39.1728),
    ("Cape Town, South Africa", -33.9249, 18.4241),
    ("Lagos, Nigeria", 6.5244, 3.3792),
    ("Karachi, Pakistan", 24.8607, 67.0011),
    ("Chennai, India", 13.0827, 80.2707),
    ("Bangkok, Thailand", 13.7563, 100.5018),
    ("Jakarta, Indonesia", -6.2088, 106.8456),
    ("Manila, Philippines", 14.5995, 120.9842),
    ("Ho Chi Minh City, Vietnam", 10.8231, 106.6297),
    ("Colombo, Sri Lanka", 6.9271, 79.8612),
    ("Port Said, Egypt", 31.2653, 32.3019),
    ("Piraeus, Greece", 37.9469, 23.6436),
    ("Genoa, Italy", 44.4056, 8.9463),
    ("Marseille, France", 43.2965, 5.3698),
    ("Valencia, Spain", 39.4699, -0.3763),
    ("Felixstowe, UK", 51.9612, 1.3511),
    ("Bremen, Germany", 53.0793, 8.8017),
]

STATUSES = [
    ('On Time', 'N/A', 'In transit - maintaining schedule'),
    ('On Time', 'N/A', '✓ On time, arrived at sorting facility'),
    ('On Time', 'N/A', 'Departed origin port on schedule'),
    ('On Time', 'N/A', 'Processing at distribution center'),
    ('Delayed', 'Port Congestion', 'Vessel delayed - severe port congestion at berth'),
    ('Delayed', 'Port Congestion', 'Port congestion - 48hr queue for dock space'),
    ('Delayed', 'Weather Delay', 'Weather delay - Typhoon warning, vessel holding position'),
    ('Delayed', 'Weather Delay', 'Severe weather - Hurricane causing delay'),
    ('Delayed', 'Customs Issue', 'Customs hold - missing documentation, awaiting paperwork'),
    ('Delayed', 'Customs Issue', 'Customs inspection in progress'),
    ('Delivered', 'N/A', '✓ Successfully delivered to recipient'),
    ('Delivered', 'N/A', 'Package delivered, signed by customer'),
]

def generate_realistic_data(num_records=150):
    events = []
    used_routes = set()
    
    for i in range(num_records):
        # Generate unique ship ID
        ship_id = f"SHP{str(i+1).zfill(6)}"
        
        # Select origin and destination (ensure they're different)
        origin_data = random.choice(PORTS)
        destination_data = random.choice([p for p in PORTS if p != origin_data])
        
        # Select a location (can be origin, destination, or intermediate)
        location_data = random.choice([origin_data, destination_data] + random.sample(PORTS, 3))
        
        # Select random status
        ai_status, ai_reason, raw_status_text = random.choice(STATUSES)
        
        # Generate timestamp (varied dates in 2025)
        base_date = datetime(2025, 10, 1)
        days_offset = random.randint(0, 28)
        hours_offset = random.randint(0, 23)
        minutes_offset = random.randint(0, 59)
        timestamp = base_date + timedelta(days=days_offset, hours=hours_offset, minutes=minutes_offset)
        
        event = {
            'shipid': ship_id,
            'origin': origin_data[0],
            'destination': destination_data[0],
            'timestamp': timestamp.strftime('%Y-%m-%dT%H:%M:%S'),
            'location': location_data[0],
            'raw_status_text': raw_status_text,
            'ai_status': ai_status,
            'ai_reason': ai_reason,
            'latitude': location_data[1],
            'longitude': location_data[2]
        }
        events.append(event)
    
    return events

# Generate the data
mock_events = generate_realistic_data(800)

# Print in the exact format requested
print("ALL_MOCK_EVENTS = [")
for i, event in enumerate(mock_events):
    comma = "," if i < len(mock_events) - 1 else ""
    print(f"    {event}{comma}")
print("]")