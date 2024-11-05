import streamlit as st
from auth import login_page, logout
import requests
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import json
import openpyxl
import io

# Set page configuration
st.set_page_config(
    page_title="Federal Capture Process Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
    <style>
    .main {
        padding: 0rem 2rem;
        background-color: #f0f2f6;
    }
    .stButton>button {
        width: 100%;
        margin-top: 10px;
        font-size: 16px;
        padding: 12px;
        background-color: #007bff;
        color: white;
        border-radius: 8px;
        border: none;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #0056b3;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        margin: 15px;
    }
    .opportunity-card {
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #ddd;
        margin: 20px 0;
        background-color: #ffffff;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .opportunity-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2);
    }
    </style>
""", unsafe_allow_html=True)

def format_currency(value):
    try:
        return f"${value:,.2f}"
    except:
        return "N/A"

def calculate_days_remaining(deadline):
    try:
        deadline_date = pd.to_datetime(deadline)
        days = (deadline_date - pd.Timestamp.now()).days
        return max(days, 0)
    except:
        return None

def fetch_opportunities(api_key, naics=None, agency=None, date_range=30, opportunity_type=None):
    base_url = "https://api.sam.gov/opportunities/v2/search"
    
    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json"
    }
    
    params = {
        "postedFrom": (datetime.now() - timedelta(days=date_range)).strftime("%m/%d/%Y"),
        "postedTo": datetime.now().strftime("%m/%d/%Y"),
        "limit": 100
    }
    
    if naics and naics.strip():
        params["ncode"] = naics.strip()
    if agency and agency.strip():
        params["organizationName"] = agency.strip()
    if opportunity_type:
        params["type"] = opportunity_type

    with st.spinner("Fetching opportunities..."):
        try:
            response = requests.get(base_url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if "opportunitiesData" in data:
                    opportunities = data["opportunitiesData"]
                    df = pd.DataFrame(opportunities)
                    
                    if 'responseDeadLine' in df.columns:
                        df['days_remaining'] = df['responseDeadLine'].apply(calculate_days_remaining)
                    
                    return df, data.get('totalRecords', 0)
            else:
                st.error(f"API Error: {response.status_code}")
                st.write(response.text)
            return None, 0
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return None, 0

def process_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        file_type = uploaded_file.type

        try:
            if file_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
                with st.spinner('Reading large Excel file... This may take a moment.'):
                    try:
                        df = pd.read_excel(uploaded_file, engine='openpyxl')  # Convert to pandas DataFrame
                    except Exception as excel_err:
                        st.error(f"Error reading Excel file: {str(excel_err)}")
                        return None
                    
                    df = df.copy()
                    
                    st.info(f"Successfully loaded file: {uploaded_file.name}")
                    st.write(f"Total rows: {len(df)}")
                    st.write(f"Total columns: {len(df.columns)}")
                    
                    return df
                    
            elif file_type == "text/csv":
                chunks = []
                chunk_size = 5000
                
                with st.spinner('Reading large CSV file in chunks...'):
                    try:
                        for chunk in pd.read_csv(uploaded_file, chunksize=chunk_size):
                            chunks.append(chunk)
                            if len(chunks) % 5 == 0:
                                st.write(f"Processed {len(chunks) * chunk_size} rows...")
                        
                        df = pd.concat(chunks, ignore_index=True)
                        st.success("File successfully loaded!")
                        return df
                    except Exception as csv_err:
                        st.error(f"Error reading CSV: {str(csv_err)}")
                        return None

            else:
                st.error(f"Unsupported file type for large files: {file_type}")
                st.info("For large files, please use Excel (.xlsx/.xls) or CSV format")
                return None

        except Exception as e:
            st.error("Error processing file")
            st.write("Debug Information:")
            st.write(f"File type: {file_type}")
            st.write(f"File size: {uploaded_file.size/1024/1024:.2f} MB")
            st.write(f"Error: {str(e)}")
            return None

def secure_api_key_input():
    return st.text_input("SAM.gov API Key", type="password", help="Your SAM.gov API key is required for data access.")

def display_metrics(df):
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
            <div class="metric-card">
                <h3>Total Opportunities</h3>
                <h2>{}</h2>
            </div>
        """.format(len(df)), unsafe_allow_html=True)
    
    with col2:
        active_opportunities = len(df[df['days_remaining'] > 0]) if 'days_remaining' in df.columns else 0
        st.markdown("""
            <div class="metric-card">
                <h3>Active Opportunities</h3>
                <h2>{}</h2>
            </div>
        """.format(active_opportunities), unsafe_allow_html=True)
    
    with col3:
        avg_response_time = df['days_remaining'].mean() if 'days_remaining' in df.columns else 0
        st.markdown("""
            <div class="metric-card">
                <h3>Avg Response Time</h3>
                <h2>{:.1f} days</h2>
            </div>
        """.format(avg_response_time), unsafe_allow_html=True)
    
    with col4:
        unique_agencies = df['fullParentPathName'].nunique() if 'fullParentPathName' in df.columns else 0
        st.markdown("""
            <div class="metric-card">
                <h3>Unique Agencies</h3>
                <h2>{}</h2>
            </div>
        """.format(unique_agencies), unsafe_allow_html=True)

def create_geographic_map(df):
    if 'placeOfPerformance' in df.columns:
        locations = df['placeOfPerformance'].dropna().unique()
        if len(locations) > 0:
            st.write("Geographic Distribution of Opportunities")
            fig = px.scatter_geo(
                df,
                locations='placeOfPerformance',
                hover_name='title',
                title="Opportunities by Location"
            )
            st.plotly_chart(fig)



    # At the start of your main() function
def main():
    if not login_page():
        return

    # Add logout button in sidebar
    if st.sidebar.button("Logout"):
        logout()
        st.rerun()

    st.title("📈 Federal Capture Process Dashboard")
    st.markdown("""
        Welcome to your enhanced federal contracting opportunities dashboard. 
        This tool helps you track and analyze opportunities from SAM.gov.
    """)

    with st.sidebar:
        st.header("🔍 Search Filters")
        
        api_key = secure_api_key_input()
        if api_key:
            st.success("API Key provided")
        
        with st.expander("📋 Basic Filters"):
            naics_code = st.text_input("NAICS Code", value="541512")
            agency_name = st.text_input("Agency Name", value="department")
            date_range = st.slider("Date Range (days)", 1, 365, 30)
        
        with st.expander("🔧 Advanced Filters"):
            opportunity_type = st.selectbox(
                "Opportunity Type",
                [None, "Solicitation", "Award Notice", "Presolicitation", "Sources Sought"]
            )
            set_aside = st.selectbox(
                "Set-Aside Type",
                [None, "Small Business", "8(a)", "HUBZone", "SDVOSB", "WOSB"]
            )

        st.sidebar.markdown("---")
        st.sidebar.header("📁 File Upload")
        uploaded_file = st.sidebar.file_uploader(
            "Upload Data File",
            type=['xlsx', 'xls', 'csv'],
            help="Upload Excel or CSV files (supports large files up to 250MB)",
            accept_multiple_files=False
        )

        if uploaded_file:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.sidebar.info(f"File Size: {file_size_mb:.2f} MB")

        data_source = st.sidebar.radio(
            "Choose Data Source",
            ["SAM.gov API", "Uploaded File"]
        )
            
        if st.button("💾 Save Current Filters"):
            current_filters = {
                "naics": naics_code,
                "agency": agency_name,
                "date_range": date_range,
                "type": opportunity_type,
                "set_aside": set_aside
            }
            st.session_state['saved_filters'] = current_filters
            st.success("Filters saved!")

    if data_source == "Uploaded File" and uploaded_file:
        try:
            if uploaded_file.type == "text/csv":
                df = pd.read_csv(uploaded_file)
            elif uploaded_file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
                df = pd.read_excel(uploaded_file, engine='openpyxl')
            
            if df is not None:
                st.success(f"Successfully loaded data from {uploaded_file.name}")
                
                st.subheader("Data Preview")
                st.dataframe(df.head())
                
                st.subheader("Column Mapping")
                st.write("Map your columns to standard fields:")
                
                standard_fields = {
                    'title': 'Opportunity Title',
                    'type': 'Opportunity Type',
                    'postedDate': 'Posted Date',
                    'responseDeadLine': 'Response Deadline',
                    'naicsCode': 'NAICS',
                    'fullParentPathName': 'Component'
                }
                
                mapping = {}
                cols = df.columns.tolist()
                
                st.write("Available columns in your file:", cols)
                
                for std_field, description in standard_fields.items():
                    mapping[std_field] = st.selectbox(
                        f"Map '{description}' to:",
                        ['None'] + cols,
                        key=f"map_{std_field}"
                    )
                
                if st.button("Apply Mapping"):
                    mapped_df = pd.DataFrame()
                    for std_field, source_field in mapping.items():
                        if source_field != 'None':
                            mapped_df[std_field] = df[source_field]
                        else:
                            if std_field == 'title':
                                mapped_df[std_field] = df['APFS Number'].astype(str) if 'APFS Number' in df.columns else 'N/A'
                            elif std_field == 'type':
                                mapped_df[std_field] = 'N/A'
                            elif std_field == 'postedDate':
                                mapped_df[std_field] = pd.Timestamp.now().strftime('%Y-%m-%d')
                            elif std_field == 'responseDeadLine':
                                mapped_df[std_field] = 'N/A'
                            elif std_field == 'naicsCode':
                                mapped_df[std_field] = df['NAICS'].astype(str) if 'NAICS' in df.columns else 'N/A'
                            elif std_field == 'fullParentPathName':
                                mapped_df[std_field] = df['Component'].astype(str) if 'Component' in df.columns else 'N/A'
                    
                    mapped_df['uiLink'] = '#'
                    
                    if not mapped_df.empty:
                        st.success("Column mapping applied successfully!")
                        df = mapped_df
                        
                        if 'responseDeadLine' in df.columns:
                            df['days_remaining'] = df['responseDeadLine'].apply(calculate_days_remaining)
                        
                        display_metrics(df)
                        
                        tabs = st.tabs([
                            "📋 Opportunities",
                            "📈 Analytics",
                            "📅 Timeline",
                            "🌍 Geographic Distribution"
                        ])
                        
                        with tabs[0]:
                            for _, row in df.iterrows():
                                st.markdown("""
                                    <div class="opportunity-card">
                                        <h3>{}</h3>
                                        <p><strong>Type:</strong> {} | <strong>Posted:</strong> {} | <strong>Deadline:</strong> {}</p>
                                        <p><strong>Agency:</strong> {}</p>
                                        <p><strong>NAICS:</strong> {}</p>
                                    </div>
                                """.format(
                                    row.get('title', 'No Title'),
                                    row.get('type', 'N/A'),
                                    row.get('postedDate', 'N/A'),
                                    row.get('responseDeadLine', 'N/A'),
                                    row.get('fullParentPathName', 'N/A'),
                                    row.get('naicsCode', 'N/A')
                                ), unsafe_allow_html=True)
                        
                        with tabs[1]:
                            if 'type' in df.columns:
                                fig = px.pie(df, names='type', title="Distribution by Type")
                                st.plotly_chart(fig)
                        
                        with tabs[2]:
                            try:
                                df['postedDate'] = pd.to_datetime(df['postedDate'], errors='coerce')
                                df['responseDeadLine'] = pd.to_datetime(df['responseDeadLine'], errors='coerce')
                                
                                df_timeline = df.dropna(subset=['postedDate', 'responseDeadLine'])
                                
                                if not df_timeline.empty:
                                    timeline_fig = px.timeline(
                                        df_timeline,
                                        x_start='postedDate',
                                        x_end='responseDeadLine',
                                        y='title',
                                        title="Opportunity Timeline"
                                    )
                                    st.plotly_chart(timeline_fig, use_container_width=True)
                                else:
                                    st.warning("No valid date data available for timeline visualization")
                            except Exception as e:
                                st.error(f"Could not create timeline: {str(e)}")
                                st.info("Timeline visualization requires valid date formats")
                        
                        with tabs[3]:
                            create_geographic_map(df)
                        
                        st.download_button(
                            "Download Processed Data",
                            df.to_csv(index=False),
                            "processed_opportunities.csv",
                            "text/csv"
                        )
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.write("Debug info:")
            st.write("File type:", uploaded_file.type)
            st.write("Error details:", str(e))

    if data_source == "SAM.gov API":
        if st.sidebar.button("🔍 Search Opportunities"):
            if not api_key:
                st.error("Please enter your SAM.gov API key")
            else:
                df, total_records = fetch_opportunities(
                    api_key, 
                    naics_code, 
                    agency_name, 
                    date_range,
                    opportunity_type
                )
                
                if df is not None and not df.empty:
                    st.success(f"Found {total_records} total records")
                    
                    display_metrics(df)
                    
                    tab1, tab2, tab3, tab4 = st.tabs([
                        "📋 Opportunities", 
                        "📈 Analytics", 
                        "🌍 Geographic Distribution",
                        "📅 Timeline"
                    ])
                    
                    with tab1:
                        col1, col2 = st.columns(2)
                        with col1:
                            sort_by = st.selectbox(
                                "Sort by",
                                ["Posted Date", "Response Deadline", "Agency"]
                            )
                        with col2:
                            filter_active = st.checkbox("Show only active opportunities")
                        
                        if filter_active:
                            df = df[df['days_remaining'] > 0]
                        
                        for _, row in df.iterrows():
                            st.markdown("""
                                <div class="opportunity-card">
                                    <h3>{}</h3>
                                    <p><strong>Type:</strong> {} | <strong>Posted:</strong> {} | <strong>Deadline:</strong> {}</p>
                                    <p><strong>Agency:</strong> {}</p>
                                    <p><strong>NAICS:</strong> {}</p>
                                </div>
                            """.format(
                                row.get('title', 'No Title'),
                                row.get('type', 'N/A'),
                                row.get('postedDate', 'N/A'),
                                row.get('responseDeadLine', 'N/A'),
                                row.get('fullParentPathName', 'N/A'),
                                row.get('naicsCode', 'N/A')
                            ), unsafe_allow_html=True)
                    
                    with tab2:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            fig1 = px.pie(
                                df, 
                                names='type', 
                                title="Distribution by Opportunity Type"
                            )
                            st.plotly_chart(fig1)
                        
                        with col2:
                            agency_counts = df['fullParentPathName'].value_counts().head(10) if 'fullParentPathName' in df.columns else []
                            fig2 = px.bar(
                                x=agency_counts.values,
                                y=agency_counts.index,
                                orientation='h',
                                title="Top 10 Agencies"
                            )
                            st.plotly_chart(fig2)
                    
                    with tab3:
                        create_geographic_map(df)
                    
                    with tab4:
                        try:
                            df['postedDate'] = pd.to_datetime(df['postedDate'], errors='coerce')
                            df['responseDeadLine'] = pd.to_datetime(df['responseDeadLine'], errors='coerce')
                            
                            df_timeline = df.dropna(subset=['postedDate', 'responseDeadLine'])
                            
                            if not df_timeline.empty:
                                timeline_fig = px.timeline(
                                    df_timeline,
                                    x_start='postedDate',
                                    x_end='responseDeadLine',
                                    y='title',
                                    title="Opportunity Timeline"
                                )
                                st.plotly_chart(timeline_fig, use_container_width=True)
                            else:
                                st.warning("No valid date data available for timeline visualization")
                        except Exception as e:
                            st.error(f"Could not create timeline: {str(e)}")
                            st.info("Timeline visualization requires valid date formats")

if __name__ == "__main__":
    main()
