import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(layout="wide", page_title="LogiTrack AI Mission Control")

# --- Auto-refresh button ---
if st.button("🔄 Refresh Data"):
    st.rerun()

st.title("🚢 LogiTrack AI: Mission Control")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# --- Fetch Data ---
try:
    response_kpi = requests.get(f"{API_URL}/api/v1/kpi/delay_reasons")
    response_kpi.raise_for_status()
    kpi_data = response_kpi.json()

    response_at_risk = requests.get(f"{API_URL}/api/v1/shipments/at_risk")
    response_at_risk.raise_for_status()
    at_risk_data = response_at_risk.json()
    
    response_live = requests.get(f"{API_URL}/api/v1/shipments/live_locations")
    response_live.raise_for_status()
    live_data = response_live.json()

except requests.exceptions.RequestException as e:
    st.error(f"Could not connect to API: {e}")
    st.info(f"Attempted to connect to: {API_URL}")
    st.stop()

# --- Summary Metrics ---
st.subheader("📊 Summary Metrics")
col1, col2, col3, col4 = st.columns(4)

total_shipments = len(live_data) if live_data else 0
delayed_shipments = len(at_risk_data) if at_risk_data else 0
on_time_shipments = total_shipments - delayed_shipments
delay_percentage = (delayed_shipments / total_shipments * 100) if total_shipments > 0 else 0

with col1:
    st.metric("Total Active Shipments", total_shipments, help="Total shipments currently being tracked")
    
with col2:
    st.metric("⚠️ Delayed", delayed_shipments, f"{delay_percentage:.1f}%", delta_color="inverse")
    
with col3:
    st.metric("✅ On Track", on_time_shipments, help="Shipments with no delays")
    
with col4:
    total_delays = sum(item['count'] for item in kpi_data) if kpi_data else 0
    st.metric("Total Delay Events", total_delays, help="Total number of delay incidents")

st.divider()

# --- LIVE MAP SECTION (NEW!) ---
st.subheader("🗺️ Live Shipment Tracking Map")

if live_data:
    try:
        df_map = pd.DataFrame(live_data)
        
        # Filter for items with valid coordinates
        df_map_filtered = df_map[
            (df_map['latitude'].notna()) & 
            (df_map['longitude'].notna())
        ].copy()
        
        if not df_map_filtered.empty:
            # Add filter options
            col_filter1, col_filter2 = st.columns(2)
            
            with col_filter1:
                status_filter = st.multiselect(
                    "Filter by Status",
                    options=['All'] + list(df_map_filtered['ai_status'].unique()),
                    default=['All']
                )
            
            with col_filter2:
                tracking_filter = st.selectbox(
                    "Filter by Tracking ID",
                    options=['All'] + list(df_map_filtered['tracking_id'].unique())
                )
            
            # Apply filters
            df_filtered = df_map_filtered.copy()
            if 'All' not in status_filter and status_filter:
                df_filtered = df_filtered[df_filtered['ai_status'].isin(status_filter)]
            if tracking_filter != 'All':
                df_filtered = df_filtered[df_filtered['tracking_id'] == tracking_filter]
            
            # Create the map using plotly
            fig_map = px.scatter_geo(
                df_filtered,
                lat='latitude',
                lon='longitude',
                hover_name='tracking_id',
                hover_data={
                    'location': True,
                    'ai_status': True,
                    'timestamp': True,
                    'latitude': ':.4f',
                    'longitude': ':.4f'
                },
                color='ai_status',
                color_discrete_map={
                    'On Time': '#00CC96',
                    'Delayed': '#EF553B',
                    'Delivered': '#636EFA',
                    None: '#AB63FA'
                },
                size_max=15,
                title='Global Shipment Locations'
            )
            
            fig_map.update_geos(
                projection_type="natural earth",
                showcountries=True,
                countrycolor="lightgray"
            )
            
            fig_map.update_layout(
                height=500,
                margin={"r":0,"t":40,"l":0,"b":0}
            )
            
            st.plotly_chart(fig_map, use_container_width=True)
            
            # Show data table below map
            st.dataframe(
                df_filtered[['tracking_id', 'location', 'ai_status', 'latitude', 'longitude', 'timestamp']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No shipments with geographic coordinates available yet.")
            
    except Exception as e:
        st.error(f"Error creating map: {e}")
        st.write("Debug - Live data:", live_data)
else:
    st.info("No live shipment data available.")

st.divider()

# --- At-Risk Shipments ---
st.subheader("⚠️ At-Risk Shipments")
if at_risk_data:
    df_at_risk = pd.DataFrame(at_risk_data)
    if 'id' in df_at_risk.columns and 'tracking_id' in df_at_risk.columns:
         cols_to_show = ['id', 'tracking_id', 'origin', 'destination']
         cols_to_show = [col for col in cols_to_show if col in df_at_risk.columns]
         st.dataframe(df_at_risk[cols_to_show], use_container_width=True, hide_index=True)
    else:
         st.dataframe(df_at_risk, use_container_width=True, hide_index=True)
else:
    st.success("✅ No shipments currently marked as delayed.")

st.divider()

# --- Two Column Layout for Charts ---
col_left, col_right = st.columns(2)

# --- Delay Reasons Chart ---
with col_left:
    st.subheader("📊 Delay Reasons Analysis")
    if kpi_data:
        try:
            df_kpi = pd.DataFrame(kpi_data)

            if not df_kpi.empty and 'ai_reason' in df_kpi.columns and 'count' in df_kpi.columns:
                df_kpi['ai_reason'] = df_kpi['ai_reason'].fillna('N/A').astype(str)
                df_kpi['count'] = pd.to_numeric(df_kpi['count'], errors='coerce').fillna(0).astype(int)
                
                df_kpi = df_kpi[df_kpi['count'] > 0]
                
                if not df_kpi.empty:
                    fig = px.bar(
                        df_kpi, 
                        x='ai_reason', 
                        y='count',
                        labels={'ai_reason': 'Delay Reason', 'count': 'Number of Events'},
                        color='count',
                        color_continuous_scale='Reds',
                        text='count'
                    )
                    
                    fig.update_layout(
                        xaxis_title="Delay Reason",
                        yaxis_title="Count",
                        showlegend=False,
                        height=400
                    )
                    
                    fig.update_traces(textposition='outside')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No delays recorded yet.")
            elif df_kpi.empty:
                 st.info("No delay data available yet.")
            else:
                 st.warning("KPI data received, but missing required fields.")
        except Exception as chart_error:
           st.error(f"Error creating chart: {chart_error}")
    else:
        st.info("No delay data available yet.")

# --- Status Distribution Pie Chart ---
with col_right:
    st.subheader("📦 Shipment Status Distribution")
    if live_data:
        try:
            df_live = pd.DataFrame(live_data)
            
            if 'ai_status' in df_live.columns:
                status_counts = df_live['ai_status'].fillna('Unknown').value_counts().reset_index()
                status_counts.columns = ['Status', 'Count']
                
                fig_pie = px.pie(
                    status_counts,
                    values='Count',
                    names='Status',
                    color='Status',
                    color_discrete_map={
                        'On Time': '#00CC96',
                        'Delayed': '#EF553B',
                        'Delivered': '#636EFA',
                        'Unknown': '#AB63FA'
                    }
                )
                
                fig_pie.update_layout(height=400)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No status data available.")
        except Exception as e:
            st.error(f"Error creating status chart: {e}")
    else:
        st.info("No live shipment data available.")

# --- Footer ---
st.divider()
st.caption("🤖 Powered by LogiTrack AI | Real-time shipment intelligence")
