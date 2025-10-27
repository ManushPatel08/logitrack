CREATE TABLE shipments (
    id SERIAL PRIMARY KEY,
    tracking_id VARCHAR(100) UNIQUE NOT NULL,
    origin VARCHAR(255),
    destination VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE shipment_events (
    id SERIAL PRIMARY KEY,
    shipment_id INTEGER REFERENCES shipments(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    location VARCHAR(255),
    raw_status_text TEXT,
    ai_status VARCHAR(50),
    ai_reason VARCHAR(100),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8)
);

-- Create indexes
CREATE INDEX idx_shipment_id ON shipment_events(shipment_id);
CREATE INDEX idx_ai_status ON shipment_events(ai_status);
CREATE INDEX idx_coordinates ON shipment_events(latitude, longitude);