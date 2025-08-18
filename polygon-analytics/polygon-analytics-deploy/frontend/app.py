import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import base64
from io import BytesIO
import plotly.express as px
import time
import threading

# API Configuration
API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Polygon Stock Analytics",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
def init_session_state():
    if "generated_code" not in st.session_state:
        st.session_state.generated_code = None
    if "output_type" not in st.session_state:
        st.session_state.output_type = None
    if "last_template_result" not in st.session_state:
        st.session_state.last_template_result = None
    if "last_execution_result" not in st.session_state:
        st.session_state.last_execution_result = None
    if "fetch_progress" not in st.session_state:
        st.session_state.fetch_progress = {"status": "idle", "message": "", "progress": 0}
    if "last_fetch_symbol" not in st.session_state:
        st.session_state.last_fetch_symbol = "AAPL"
    if "last_prompt" not in st.session_state:
        st.session_state.last_prompt = ""
    if "saved_templates_cache" not in st.session_state:
        st.session_state.saved_templates_cache = []

init_session_state()

st.title("📈 Polygon Stock Analytics Platform")
st.markdown("Fetch tick data from Polygon and generate analytics using AI")

# Sidebar for navigation
with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Select Page",
        ["Data Fetcher", "Analytics Generator", "Saved Templates", "Query History"]
    )
    
    st.divider()
    
    # Session info
    st.subheader("📊 Session Info")
    if st.session_state.generated_code:
        st.success("✅ Template loaded")
    if st.session_state.last_fetch_symbol:
        st.info(f"Last symbol: {st.session_state.last_fetch_symbol}")
    
    if st.button("🔄 Clear Session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        init_session_state()
        st.rerun()

# Data Fetcher Page with Progress
if page == "Data Fetcher":
    st.header("📥 Fetch Stock Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        symbol = st.text_input(
            "Stock Symbol", 
            value=st.session_state.last_fetch_symbol, 
            help="Enter stock ticker symbol"
        )
    
    with col2:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=7),
            max_value=datetime.now()
        )
    
    with col3:
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            max_value=datetime.now()
        )
    
    # Progress container
    progress_container = st.container()
    
    if st.button("🔄 Fetch Data", type="primary"):
        st.session_state.last_fetch_symbol = symbol.upper()
        
        # Calculate estimated time
        days_to_fetch = (end_date - start_date).days + 1
        estimated_time = days_to_fetch * 5  # Estimate 5 seconds per day
        
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Start fetch with progress updates
            status_text.text(f"Starting fetch for {symbol.upper()}...")
            progress_bar.progress(10)
            
            try:
                # Make the API request
                status_text.text(f"Connecting to Polygon API...")
                progress_bar.progress(20)
                
                response = requests.post(
                    f"{API_URL}/api/fetch-data",
                    json={
                        "symbol": symbol.upper(),
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d")
                    },
                    stream=True,
                    timeout=300  # 5 minute timeout
                )
                
                # Simulate progress during fetch
                if response.status_code == 200:
                    # Update progress incrementally
                    for i in range(30, 90, 10):
                        progress_bar.progress(i)
                        status_text.text(f"Fetching tick data... ({i}%)")
                        time.sleep(estimated_time / 10)
                    
                    progress_bar.progress(100)
                    result = response.json()
                    
                    st.success(f"✅ {result['message']}")
                    
                    # Show data summary
                    summary_response = requests.get(
                        f"{API_URL}/api/data-summary",
                        params={"symbol": symbol.upper()}
                    )
                    
                    if summary_response.status_code == 200:
                        summary = summary_response.json()
                        
                        # Display summary in metrics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Symbol", symbol.upper())
                        with col2:
                            st.metric("Total Records", f"{summary['record_count']:,}")
                        with col3:
                            if summary["date_range"]:
                                st.metric("Date Range", 
                                    f"{summary['date_range']['start'][:10]} to {summary['date_range']['end'][:10]}")
                else:
                    st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                    
            except requests.exceptions.Timeout:
                st.warning("⏱️ Request is taking longer than expected. Data fetch continues in background.")
                st.info("You can switch tabs and check back later.")
            except Exception as e:
                st.error(f"Failed to fetch data: {str(e)}")
            finally:
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()

# Analytics Generator Page with Persistence
elif page == "Analytics Generator":
    st.header("🤖 Generate Analytics Templates")
    
    # Show if template is loaded
    if st.session_state.generated_code:
        st.info("📝 Template loaded from previous generation. Generate a new one or execute below.")
    
    # Template generation section
    st.subheader("Create New Template")
    
    prompt = st.text_area(
        "Describe your analysis in plain English",
        value=st.session_state.last_prompt,
        placeholder="Example: Show me volume by hour for today with a bar chart",
        height=100
    )
    
    col1, col2 = st.columns(2)
    with col1:
        save_template = st.checkbox("Save as template")
    
    with col2:
        template_name = st.text_input("Template Name (optional)") if save_template else None
    
    if st.button("🎯 Generate Template", type="primary"):
        if prompt:
            st.session_state.last_prompt = prompt
            
            with st.spinner("Generating template with AI..."):
                progress_placeholder = st.empty()
                progress_placeholder.info("🤖 Sending request to GPT-4...")
                
                try:
                    response = requests.post(
                        f"{API_URL}/api/generate-template",
                        json={
                            "prompt": prompt,
                            "save_template": save_template,
                            "template_name": template_name
                        },
                        timeout=30
                    )
                    
                    progress_placeholder.empty()
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ Template generated successfully!")
                        
                        # Save to session state
                        st.session_state.generated_code = result["code"]
                        st.session_state.output_type = result["output_type"]
                        st.session_state.last_template_result = result
                        
                        # Display generated code
                        with st.expander("📄 View Generated Python Code", expanded=True):
                            st.code(result["code"], language="python")
                        
                        if save_template:
                            st.info(f"💾 Template saved with ID: {result.get('template_id')}")
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                        
                except Exception as e:
                    st.error(f"Failed to generate template: {str(e)}")
                    progress_placeholder.empty()
        else:
            st.warning("Please enter a prompt")
    
    # Template execution section
    if st.session_state.generated_code:
        st.divider()
        st.subheader("▶️ Execute Template")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            exec_symbol = st.text_input(
                "Symbol for Execution", 
                value=st.session_state.last_fetch_symbol or "AAPL"
            )
        
        with col2:
            exec_start = st.date_input(
                "Start Date for Execution",
                value=datetime.now() - timedelta(days=1),
                key="exec_start"
            )
        
        with col3:
            exec_end = st.date_input(
                "End Date for Execution",
                value=datetime.now(),
                key="exec_end"
            )
        
        if st.button("▶️ Execute Template", type="primary"):
            with st.spinner("Executing template..."):
                exec_progress = st.progress(0)
                exec_status = st.empty()
                
                try:
                    exec_progress.progress(25)
                    exec_status.text("Preparing execution environment...")
                    
                    response = requests.post(
                        f"{API_URL}/api/execute-template",
                        json={
                            "template_code": st.session_state.generated_code,
                            "symbol": exec_symbol.upper(),
                            "start_date": exec_start.strftime("%Y-%m-%d"),
                            "end_date": exec_end.strftime("%Y-%m-%d")
                        },
                        timeout=60
                    )
                    
                    exec_progress.progress(75)
                    exec_status.text("Processing results...")
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        exec_progress.progress(100)
                        exec_status.empty()
                        exec_progress.empty()
                        
                        if result["success"]:
                            st.session_state.last_execution_result = result
                            output = result["result"]
                            
                            # Display results based on type
                            if output.get("type") in ["table", "both"]:
                                st.subheader("📊 Data Table")
                                if "data" in output:
                                    data = output["data"]
                                    
                                    try:
                                        # Create DataFrame directly
                                        if isinstance(data, dict) and len(data) == 0:
                                            st.info("Query returned no data")
                                        else:
                                            df = pd.DataFrame(data)
                                            
                                            if not df.empty:
                                                # Display the dataframe
                                                st.dataframe(df, use_container_width=True)
                                                
                                                # Add metrics
                                                col1, col2 = st.columns(2)
                                                with col1:
                                                    st.metric("Rows", len(df))
                                                with col2:
                                                    st.metric("Columns", len(df.columns))
                                                
                                                # Add download button
                                                csv = df.to_csv(index=False)
                                                st.download_button(
                                                    label="📥 Download CSV",
                                                    data=csv,
                                                    file_name=f"{exec_symbol}_{exec_start}_{exec_end}.csv",
                                                    mime="text/csv"
                                                )
                                            else:
                                                st.info("Query returned an empty dataset")
                                                
                                    except Exception as e:
                                        st.error(f"Error creating table: {str(e)}")
                                        st.code(f"Data structure: {str(data)[:500]}", language="json")
                                else:
                                    st.warning("No data field in response")
                            
                            if output.get("type") in ["chart", "both"]:
                                st.subheader("📈 Visualization")
                                if "chart" in output and output["chart"]:
                                    img_data = base64.b64decode(output["chart"])
                                    st.image(img_data)
                                    
                                    # Add download button for chart
                                    st.download_button(
                                        label="📥 Download Chart",
                                        data=img_data,
                                        file_name=f"{exec_symbol}_chart_{exec_start}.png",
                                        mime="image/png"
                                    )
                        else:
                            st.error(f"Execution failed: {result.get('error')}")
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                        
                except Exception as e:
                    st.error(f"Failed to execute template: {str(e)}")
                finally:
                    exec_progress.empty()
                    exec_status.empty()
    else:
        st.info("👆 Generate a template above to execute it")

# Saved Templates Page
elif page == "Saved Templates":
    st.header("💾 Saved Templates")
    
    # Fetch templates
    try:
        response = requests.get(f"{API_URL}/api/templates")
        if response.status_code == 200:
            templates = response.json()
            st.session_state.saved_templates_cache = templates
            
            if templates:
                for template in templates:
                    with st.expander(f"📋 {template['name']} - {template['created_at']}"):
                        st.write(f"**Description:** {template.get('description', 'N/A')}")
                        st.write(f"**Prompt:** {template['prompt']}")
                        st.write(f"**Output Type:** {template['output_type']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"Load Template", key=f"load_{template['id']}"):
                                # Fetch full template details
                                detail_response = requests.get(f"{API_URL}/api/template/{template['id']}")
                                if detail_response.status_code == 200:
                                    detail = detail_response.json()
                                    st.session_state.generated_code = detail["code"]
                                    st.session_state.output_type = detail["output_type"]
                                    st.success("Template loaded! Go to Analytics Generator to execute.")
                        
                        with col2:
                            if st.button(f"View Code", key=f"view_{template['id']}"):
                                detail_response = requests.get(f"{API_URL}/api/template/{template['id']}")
                                if detail_response.status_code == 200:
                                    detail = detail_response.json()
                                    st.code(detail["code"], language="python")
            else:
                st.info("No saved templates yet. Generate and save templates in the Analytics Generator.")
                
    except Exception as e:
        st.error(f"Failed to fetch templates: {str(e)}")

# Query History Page
elif page == "Query History":
    st.header("📜 Query History")
    st.info("Query history feature coming soon...")
    
    # Show last execution result if available
    if st.session_state.last_execution_result:
        st.subheader("Last Execution Result")
        result = st.session_state.last_execution_result
        if result["success"]:
            output = result["result"]
            if output.get("type") in ["table", "both"] and "data" in output:
                df = pd.DataFrame(output["data"])
                st.dataframe(df, use_container_width=True)