import os
import time
import warnings
import pandas as pd
import requests
import streamlit as st
from datetime import datetime

# Plotly (Check if available)
try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

warnings.filterwarnings("ignore")

# --- Configuration ---
API_URL = os.environ.get("API_URL", "http://localhost:8000") # Get API URL from environment or default
REFRESH_SEC = 15 # Auto-refresh interval

# --------------------- Page Setup & Styling ---------------------
st.set_page_config(
    page_title="LogiTrack AI | Real-Time Shipment Intelligence",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Custom CSS for Modern Look & Larger Fonts ---
st.markdown(f"""
<style>
    /* Base font size */
    html {{
        font-size: 16px; /* Adjust base font size */
    }}

    /* App background */
    .stApp {{
        background-color: #f0f2f6; /* Lighter grey background */
    }}

    /* Main container styling (modern card) */
    .main .block-container {{
        background-color: #ffffff;
        border-radius: 12px;
        padding: 2rem 2.5rem 3rem; /* Adjust padding */
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); /* Softer shadow */
        border: 1px solid #e0e0e0; /* Subtle border */
        margin-top: 1rem;
        margin-bottom: 2rem;
    }}

    /* Header styling */
    h1 {{ /* Main Title - Not used directly in app.py but good to define */
        color: #1a1a2e;
        font-weight: 700;
        font-size: 2.2rem !important; /* Slightly larger */
        margin-bottom: 0.5rem;
    }}
    h2 {{ /* Section Header: LogiTrack AI */
        color: #1a1a2e;
        font-weight: 600;
        font-size: 1.8rem !important; /* Larger */
        margin-bottom: 0.2rem;
        border-bottom: 2px solid #667eea; /* Accent line */
        padding-bottom: 0.3rem;
        display: inline-block; /* Keep border tight */
    }}
     h3 {{ /* Sub-section Headers: Mission Control, Global Tracking etc. */
        color: #4a4a4a;
        font-weight: 600;
        font-size: 1.5rem !important; /* Larger */
        margin-top: 2rem;
        margin-bottom: 1rem;
    }}
     h4 {{ /* Chart Titles */
        color: #5a5a5a;
        font-weight: 500;
        font-size: 1.2rem !important; /* Larger */
        margin-bottom: 0.8rem;
    }}

    /* Subtitle/Timestamp text */
    .metric-sub {{
        color: #555; /* Darker grey */
        font-size: 0.95rem; /* Slightly larger */
        margin-bottom: 1.5rem;
    }}

    /* Metric styles */
    .stMetric {{
        background-color: #f9f9fb;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        border: 1px solid #e8e8e8;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    }}
    .stMetric > label {{ /* Metric label (e.g., "Active Shipments") */
       font-weight: 500;
       color: #333;
    }}
     .stMetric > div {{ /* Metric value */
       font-weight: 600;
       font-size: 1.6rem; /* Larger value */
    }}
    .stMetric .st-emotion-cache-1xarl3l {{ /* Delta value */
        font-size: 0.9rem; /* Slightly larger delta */
    }}

    /* Plotly chart container */
    .js-plotly-plot {{
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #ddd; /* Subtle border for charts */
    }}

    /* Horizontal Rule */
    hr {{
        height: 1px;
        border: none;
        margin: 2rem 0; /* Increase spacing */
        background-color: #e0e0e0; /* Simple grey line */
    }}

    /* Custom button style for refresh */
    .stButton > button {{
        border-radius: 8px;
        padding: 0.4rem 1rem;
        font-weight: 500;
    }}

    /* Dataframe styling */
    .stDataFrame {{
        border-radius: 8px;
        overflow: hidden; /* Ensures border radius applies to content */
    }}

</style>
""", unsafe_allow_html=True)

# --------------------- Auto Refresh Logic ---------------------
colR1, colR2 = st.columns([4, 1]) # Adjust column ratio
with colR1:
    st.caption("") # Placeholder to align button if needed
with colR2:
    if st.button("🔄 Refresh Now"):
        st.rerun()
    st.caption(f"Auto-refresh in {REFRESH_SEC}s")

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh >= REFRESH_SEC:
    st.session_state.last_refresh = time.time()
    st.rerun()

# --------------------- Header ---------------------
st.markdown("## 🚢 LogiTrack AI")
st.markdown(
    f"<div class='metric-sub'>Real-Time Shipment Intelligence • Last updated: "
    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>",
    unsafe_allow_html=True,
)

# --------------------- Fetch Data from Backend API ---------------------
@st.cache_data(ttl=REFRESH_SEC - 5) # Cache data briefly
def fetch_json(path: str):
    """Fetches JSON data from the API endpoint."""
    try:
        r = requests.get(f"{API_URL}{path}", timeout=10) # Shorter timeout
        r.raise_for_status() # Raise error for bad status codes
        return r.json()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Could not connect to API: {e}")
        st.info(f"Attempted URL: {API_URL}{path}")
        return None # Return None on error

# Fetch all data points
kpi_data = fetch_json("/api/v1/kpi/delay_reasons")
at_risk_data = fetch_json("/api/v1/shipments/at_risk")
live_data = fetch_json("/api/v1/shipments/live_locations")

# Stop execution if essential data failed to load
if live_data is None or at_risk_data is None or kpi_data is None:
    st.warning("Could not fetch essential data from the API. Please check backend status.")
    st.stop()


# --------------------- Key Performance Indicators (KPIs) ---------------------
st.markdown("### 📊 Mission Control")

# Calculate KPIs safely, handling potential empty data
total_shipments = len(live_data)
delayed_shipments = len(at_risk_data)
on_time_shipments = max(total_shipments - delayed_shipments, 0)
delay_pct = (delayed_shipments / total_shipments * 100) if total_shipments > 0 else 0
total_delays = sum(item.get("count", 0) for item in kpi_data)

# Display Metrics
m1, m2, m3, m4 = st.columns(4)
with m1: st.metric("🌍 Active Shipments", total_shipments)
# Use 'inverse' delta color for negative meaning (delays are bad)
with m2: st.metric("⚠️ At Risk", delayed_shipments, f"{delay_pct:.1f}% Delayed", delta_color="inverse")
with m3: st.metric("✅ On Track", on_time_shipments)
with m4: st.metric("🚨 Total Delay Incidents", total_delays)

st.markdown("<hr>", unsafe_allow_html=True)

# --------------------- Globe Map (Plotly) ---------------------
st.markdown("### 🗺️ Global Shipment Tracking")

if PLOTLY_AVAILABLE and live_data:
    df_map = pd.DataFrame(live_data)
    # Ensure coordinates exist before plotting
    df_map = df_map.dropna(subset=['latitude', 'longitude']).copy()

    if not df_map.empty:
        # --- Filters ---
        f1, f2 = st.columns(2)
        with f1:
            # Dynamically get statuses from data, including 'Unknown' if present
            available_statuses = df_map["ai_status"].fillna("Unknown").unique()
            statuses_options = ["All"] + sorted([s for s in available_statuses])
            status_filter = st.multiselect("Filter by Status", statuses_options, default=["All"])
        with f2:
            ids_options = ["All"] + sorted(df_map["tracking_id"].unique().tolist())
            tracking_filter = st.selectbox("Filter by Tracking ID", ids_options)

        # Apply filters
        df_filtered = df_map.copy()
        if status_filter and "All" not in status_filter:
            # Handle filtering for 'Unknown' (None/NaN) values
            if "Unknown" in status_filter:
                status_to_check = [s for s in status_filter if s != "Unknown"]
                df_filtered = df_filtered[
                    df_filtered["ai_status"].isin(status_to_check) | df_filtered["ai_status"].isna()
                ]
            else:
                 df_filtered = df_filtered[df_filtered["ai_status"].isin(status_filter)]
        if tracking_filter != "All":
            df_filtered = df_filtered[df_filtered["tracking_id"] == tracking_filter]

        # --- Plotting ---
        if not df_filtered.empty:
            color_map = {
                "On Time": "#28a745", # Green
                "Delayed": "#dc3545", # Red
                "Delivered": "#007bff", # Blue
                "Unknown": "#6f42c1", # Purple for unknown/null
                None: "#6f42c1" # Ensure None maps correctly
            }

            # Replace None with "Unknown" for coloring and legend
            df_filtered["ai_status_display"] = df_filtered["ai_status"].fillna("Unknown")

            fig = px.scatter_geo(
                df_filtered,
                lat="latitude",
                lon="longitude",
                hover_name="tracking_id",
                hover_data={ # Customize hover data
                    "location": True,
                    "ai_status_display": True,
                    "timestamp": True,
                    "latitude": ':.4f', # Format coordinates
                    "longitude": ':.4f',
                    "ai_status": False, # Hide original ai_status if needed
                    "ai_status_display": False # Hide display version from default hover
                },
                color="ai_status_display", # Use display version for color
                color_discrete_map=color_map,
                size_max=15, # Slightly smaller points
                opacity=0.8,
                title="Live Shipment Locations"
            )

            fig.update_geos(
                projection_type="natural earth", # Different projection
                showcountries=True, countrycolor="#bbb",
                showocean=True, oceancolor="#ddeeff",
                showland=True, landcolor="#f8f8f8",
                showlakes=False,
                bgcolor="rgba(0,0,0,0)" # Transparent background for geo
            )
            fig.update_layout(
                height=580,
                margin=dict(l=0, r=0, t=40, b=0), # Added top margin for title
                paper_bgcolor="rgba(0,0,0,0)", # Transparent background
                plot_bgcolor="rgba(0,0,0,0)",
                legend_title_text="Shipment Status",
                geo=dict()
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- Expandable Data Table ---
            with st.expander("🔍 View Detailed Map Data"):
                # Select and rename columns for clarity in the table
                display_cols = {
                     "tracking_id": "Tracking ID",
                     "location": "Last Location",
                     "ai_status_display": "Status",
                     "latitude": "Latitude",
                     "longitude": "Longitude",
                     "timestamp": "Timestamp"
                 }
                df_display = df_filtered[display_cols.keys()].rename(columns=display_cols)
                # Format timestamp for better readability
                df_display["Timestamp"] = pd.to_datetime(df_display["Timestamp"]).dt.strftime('%Y-%m-%d %H:%M')
                st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("No shipments match the selected filters.")
    else:
        st.info("🕒 Waiting for shipment data with coordinates...")
else:
    st.info("🕒 No live shipment data available to display on the map.")

st.markdown("<hr>", unsafe_allow_html=True)

# --------------------- At-Risk Shipments Table ---------------------
st.markdown("### ⚠️ Priority Alert: At-Risk Shipments")
if at_risk_data:
    df_risk = pd.DataFrame(at_risk_data)
    # Ensure columns exist before trying to display them
    cols_to_display = ["tracking_id", "origin", "destination"]
    available_cols = [col for col in cols_to_display if col in df_risk.columns]

    if not df_risk.empty and available_cols:
         # Rename columns for presentation
         risk_display_cols = {
             "tracking_id": "Tracking ID",
             "origin": "Origin",
             "destination": "Destination"
         }
         df_risk_display = df_risk[available_cols].rename(columns=risk_display_cols)
         st.dataframe(df_risk_display, use_container_width=True, hide_index=True)
    elif not df_risk.empty:
         # Fallback if standard columns aren't there
         st.dataframe(df_risk, use_container_width=True, hide_index=True)
    else: # This case is now covered by the outer if
         st.success("✅ Excellent! No shipments currently classified as 'At Risk'.")
else:
     st.success("✅ Excellent! No shipments currently classified as 'At Risk'.")


st.markdown("<hr>", unsafe_allow_html=True)

# --------------------- Analytics Section ---------------------
st.markdown("### 📈 Analytics & Insights")
a1, a2 = st.columns(2)

# --- Delay Reasons Bar Chart ---
with a1:
    st.markdown("<h4>Reasons for Delay</h4>", unsafe_allow_html=True)
    if kpi_data:
        df_kpi = pd.DataFrame(kpi_data)

        # Clean and validate data
        if not df_kpi.empty and {"ai_reason", "count"}.issubset(df_kpi.columns):
            df_kpi["ai_reason"] = df_kpi["ai_reason"].fillna("Unknown")
            df_kpi = df_kpi[df_kpi["ai_reason"] != "N/A"] # Exclude 'N/A' reasons
            df_kpi["count"] = pd.to_numeric(df_kpi["count"], errors='coerce').fillna(0).astype(int)
            df_kpi = df_kpi[df_kpi["count"] > 0] # Filter out zero counts

            if not df_kpi.empty:
                fig_bar = px.bar(
                    df_kpi.sort_values("count", ascending=False), # Sort bars
                    x="ai_reason",
                    y="count",
                    text="count",
                    color="count",
                    color_continuous_scale=px.colors.sequential.Reds, # Red color scale
                    labels={"ai_reason": "Delay Reason", "count": "Number of Incidents"},
                    title="Breakdown of Delay Incidents by Reason"
                )
                fig_bar.update_layout(
                    height=350,
                    showlegend=False,
                    xaxis_title=None, # Cleaner look
                    yaxis_title="Incidents",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=50, b=10), # Adjust margins
                    coloraxis_showscale=False # Hide color scale bar
                )
                fig_bar.update_traces(textposition='outside')
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No recorded delay incidents with specific reasons.")
        else:
            st.info("Delay reason data is unavailable or malformed.")
    else:
        st.info("No delay reason data available from API.")

# --- Status Distribution Pie Chart ---
with a2:
    st.markdown("<h4>Shipment Status Distribution</h4>", unsafe_allow_html=True)
    if live_data:
        df_live = pd.DataFrame(live_data)
        if "ai_status" in df_live.columns and not df_live.empty:
            # Get value counts, handling potential None/NaN
            status_counts = df_live["ai_status"].fillna("Unknown").value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]

            # Define colors
            pie_color_map = {
                "On Time": "#28a745",
                "Delayed": "#dc3545",
                "Delivered": "#007bff",
                "Unknown": "#6f42c1",
            }

            fig_pie = px.pie(
                status_counts,
                values="Count",
                names="Status",
                hole=0.5, # Doughnut chart
                color="Status",
                color_discrete_map=pie_color_map,
                title="Overall Distribution of Current Shipment Statuses"
            )
            fig_pie.update_layout(
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=50, b=10, l=0, r=0),
                legend_title_text="Status"
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("📊 Status data is missing or unavailable.")
    else:
        st.info("📊 No live shipment data available for status distribution.")


# --------------------- System Status Footer ---------------------
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("### ⚙️ System Status")
s1, s2, s3 = st.columns(3)

with s1:
    try:
        health_api = requests.get(f"{API_URL}/health", timeout=5)
        if health_api.status_code == 200:
            st.success("✅ API: Online")
        else:
            st.error(f"❌ API Error: Status {health_api.status_code}")
    except requests.exceptions.RequestException:
        st.error("❌ API: Offline")

with s2:
    try:
        health_db = requests.get(f"{API_URL}/health/db", timeout=5)
        db_status = health_db.json()
        if health_db.status_code == 200 and db_status.get("database") == "connected":
            st.success("✅ Database: Connected")
        else:
            st.error(f"❌ DB Error: {db_status.get('detail', 'Connection Failed')}")
    except requests.exceptions.RequestException:
        st.error("❌ Database: Unreachable")

with s3:
    # Check if worker seems active based on data presence
    if total_shipments > 0:
        st.success(f"✅ Worker: Assumed Active ({total_shipments} shipments)")
    else:
        st.warning("⚠️ Worker: No data detected (or worker offline)")

# --------------------- Footer ---------------------
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center; color:#777; font-size: 0.85rem;'>" # Adjusted style
    "Built with FastAPI • PostgreSQL • Streamlit • Plotly • Docker"
    "</div>",
    unsafe_allow_html=True,
)