# app.py
import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime
import altair as alt

# Set page configuration
st.set_page_config(
    page_title="Lambda Function Manager",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define API endpoints
API_BASE_URL = "http://localhost:8000"

# Sidebar for navigation
st.sidebar.title("Lambda Function Manager")
page = st.sidebar.radio("Navigation", ["Functions", "Deploy Function", "Execute Function", "Monitoring Dashboard"])

# Helper functions for API calls
def get_functions():
    try:
        response = requests.get(f"{API_BASE_URL}/functions/list")
        if response.status_code == 200:
            # Make sure to return a dictionary, not a string
            return response.json()
        else:
            st.error(f"Error: {response.status_code}")
            return {}
    except requests.exceptions.RequestException as e:
        st.error(f"API connection error: {e}")
        return {}

def get_function_details(function_name):
    try:
        response = requests.get(f"{API_BASE_URL}/functions/get/{function_name}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching function details: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"API connection error: {e}")
        return None

def get_function_metrics(function_name):
    try:
        response = requests.get(f"{API_BASE_URL}/functions/metrics/{function_name}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching metrics: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"API connection error: {e}")
        return None

# Function List Page
if page == "Functions":
    st.title("Function Management")
    
    # Refresh button
    if st.button("Refresh Functions"):
        st.experimental_rerun()
    
    functions = get_functions()
    
    if not functions:
        st.info("No functions are registered. Go to Deploy Function page to create one.")
    else:
        # Convert functions dictionary to a list of dictionaries for display
        function_list = []
        for name, details in functions.items():
            # Make sure details is a dictionary, not a string
            if isinstance(details, dict):
                function_list.append({
                    "Name": name,
                    "Route": details.get("route", ""),
                    "Language": details.get("language", ""),
                    "Timeout (seconds)": details.get("timeout", 0)
                })
            else:
                # If details is not a dictionary, create a simpler entry
                function_list.append({
                    "Name": name,
                    "Details": str(details)
                })
        
        # Display function table
        st.dataframe(pd.DataFrame(function_list), use_container_width=True)
        
        # Select function for actions
        selected_function = st.selectbox("Select Function", list(functions.keys()))
        
        col1, col2, col3 = st.columns(3)
        
        # View details button
        with col1:
            if st.button("View Details"):
                details = get_function_details(selected_function)
                if details:
                    st.json(details)
        
        # Delete function button
        with col2:
            if st.button("Delete Function"):
                try:
                    response = requests.delete(f"{API_BASE_URL}/functions/delete/{selected_function}")
                    if response.status_code == 200:
                        st.success(f"Function {selected_function} deleted successfully!")
                        time.sleep(1)  # Give user time to see the message
                        st.experimental_rerun()
                    else:
                        st.error(f"Failed to delete function: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Error: {e}")
        
        # View metrics button
        with col3:
            if st.button("View Metrics"): 
                metrics = get_function_metrics(selected_function)
                if metrics:
                    st.subheader(f"Metrics for {selected_function}")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Average Duration (seconds)", f"{metrics.get('average_duration') or 0.0:.4f}")
                    with col2:
                        st.metric("Total Invocations", metrics.get("total_invocations", 0))

# Deploy Function Page
elif page == "Deploy Function":
    st.title("Deploy New Function")
    
    # Check if editing an existing function
    functions = get_functions()
    edit_mode = st.checkbox("Edit Existing Function")
    
    if edit_mode and functions:
        function_to_edit = st.selectbox("Select Function to Edit", list(functions.keys()))
        function_details = get_function_details(function_to_edit)
        
        if function_details and isinstance(function_details, dict):
            # Pre-fill form with existing values
            name = st.text_input("Function Name", value=function_details.get("name", ""), disabled=True)
            route = st.text_input("Route", value=function_details.get("route", ""))
            language = st.selectbox("Language", ["python", "javascript"], 
                                  index=0 if function_details.get("language") == "python" else 1)
            timeout = st.slider("Timeout (seconds)", min_value=1, max_value=300, 
                              value=function_details.get("timeout", 10))
            
            if st.button("Update Function"):
                data = {
                    "name": name,
                    "route": route,
                    "language": language,
                    "timeout": timeout
                }
                try:
                    response = requests.put(f"{API_BASE_URL}/functions/update/{name}", json=data)
                    if response.status_code == 200:
                        st.success(f"Function {name} updated successfully!")
                    else:
                        st.error(f"Failed to update function: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Error: {e}")
        else:
            st.error("Could not load function details or invalid format")
    else:
        # Form for new function
        with st.form("deploy_function_form"):
            name = st.text_input("Function Name")
            route = st.text_input("Route (e.g., /hello)")
            language = st.selectbox("Language", ["python", "javascript"])
            timeout = st.slider("Timeout (seconds)", min_value=1, max_value=300, value=10)
            
            submitted = st.form_submit_button("Deploy Function")
            if submitted:
                if not name or not route:
                    st.error("Name and route are required!")
                else:
                    data = {
                        "name": name,
                        "route": route,
                        "language": language,
                        "timeout": timeout
                    }
                    try:
                        response = requests.post(f"{API_BASE_URL}/functions/register", json=data)
                        if response.status_code == 200:
                            st.success(f"Function {name} deployed successfully!")
                        else:
                            st.error(f"Failed to deploy function: {response.status_code}")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Error: {e}")

# Execute Function Page
elif page == "Execute Function":
    st.title("Execute Function")
    
    runtime_options = ["docker", "docker-warm"]
    if "second_runtime" in st.session_state:
        runtime_options.append(st.session_state.second_runtime)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        function_code = st.text_area("Function Code", 
                                    value='print("Hello Lambda!")', 
                                    height=300)
    
    with col2:
        language = st.selectbox("Language", ["python", "javascript"])
        runtime = st.selectbox("Runtime", runtime_options)
        
        if st.button("Execute", type="primary"):
            execute_data = {
                "functionCode": function_code,
                "language": language,
                "runtime": runtime
            }
            
            try:
                with st.spinner("Executing function..."):
                    start_time = time.time()
                    response = requests.post(f"{API_BASE_URL}/functions/execute", json=execute_data)
                    execution_time = time.time() - start_time
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        st.subheader("Execution Results")
                        st.text("Standard Output:")
                        st.code(result.get("stdout", ""))
                        
                        if result.get("stderr"):
                            st.text("Standard Error:")
                            st.code(result.get("stderr"))
                        
                        # Display execution metrics
                        st.subheader("Execution Metrics")
                        metrics = result.get("metrics", {})
                        
                        metric_cols = st.columns(4)
                        metric_cols[0].metric("Duration (s)", f"{metrics.get('duration', 0):.4f}")
                        metric_cols[1].metric("API Latency (s)", f"{execution_time:.4f}")
                        metric_cols[2].metric("CPU (%)", metrics.get("cpu_percent", 0))
                        metric_cols[3].metric("Memory (MB)", metrics.get("memory_mb", 0))
                    else:
                        st.error(f"Execution failed: {response.status_code}")
                        st.text(response.text)
            except requests.exceptions.RequestException as e:
                st.error(f"Error: {e}")

# Monitoring Dashboard Page
elif page == "Monitoring Dashboard":
    st.title("Function Monitoring Dashboard")
    
    functions = get_functions()
    
    if not functions:
        st.info("No functions available to monitor.")
    else:
        # System-wide statistics
        st.header("System-wide Statistics")
        
        # Create placeholder data for demo if needed
        # In a real implementation, you would fetch these from the API
        
        # Placeholder charts with mock data (replace with real data in production)
        col1, col2 = st.columns(2)
        
        with col1:
            # Invocations over time chart
            st.subheader("Function Invocations")
            
            # Mock data for visualization - replace with real API data
            dates = pd.date_range(start='2025-04-01', periods=14)
            invocation_data = pd.DataFrame({
                'date': dates,
                'count': [12, 18, 25, 22, 30, 35, 28, 15, 20, 25, 40, 45, 30, 25]
            })
            
            invocation_chart = alt.Chart(invocation_data).mark_line().encode(
                x='date:T',
                y='count:Q',
                tooltip=['date:T', 'count:Q']
            ).properties(height=300)
            
            st.altair_chart(invocation_chart, use_container_width=True)
        
        with col2:
            # Average execution time chart
            st.subheader("Average Execution Time")
            
            # Mock data for visualization - replace with real API data
            execution_data = pd.DataFrame({
                'date': dates,
                'time': [0.8, 1.2, 0.9, 1.5, 1.3, 1.0, 0.7, 0.9, 1.1, 1.3, 1.5, 1.2, 1.0, 0.8]
            })
            
            execution_chart = alt.Chart(execution_data).mark_line(color='orange').encode(
                x='date:T',
                y='time:Q',
                tooltip=['date:T', 'time:Q']
            ).properties(height=300)
            
            st.altair_chart(execution_chart, use_container_width=True)
        
        # Individual function metrics
        st.header("Individual Function Metrics")
        selected_function = st.selectbox("Select Function", list(functions.keys()))
        
        if selected_function:
            metrics = get_function_metrics(selected_function)
            
            if metrics:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Total Invocations", metrics.get("total_invocations", 0))
                
                with col2:
                    st.metric("Average Duration (seconds)", f"{metrics.get('average_duration') or 0.0:.4f}")
                
                # Performance comparison between runtimes - FIXED CHART
                st.subheader("Performance by Runtime")
                
                # Mock data for visualization - replace with real API data
                runtime_data = pd.DataFrame({
                    'Runtime': ['docker', 'docker-warm', 'second-runtime'],
                    'Average Duration (s)': [1.5, 0.3, 0.8],
                    'Invocations': [50, 120, 30]
                })
                
                # Create a figure with secondary y-axis for better visualization
                fig = go.Figure()
                
                # Add bars for average duration
                fig.add_trace(go.Bar(
                    x=runtime_data['Runtime'],
                    y=runtime_data['Average Duration (s)'],
                    name='Avg Duration',
                    marker_color='indianred'
                ))
                
                # Add bars for invocations on secondary y-axis
                fig.add_trace(go.Bar(
                    x=runtime_data['Runtime'],
                    y=runtime_data['Invocations'],
                    name='Invocations',
                    marker_color='lightsalmon',
                    yaxis='y2'
                ))
                
                # Set up the layout with a secondary y-axis
                fig.update_layout(
                    height=400,
                    yaxis=dict(
                        title='Average Duration (s)',
                        side='left'
                    ),
                    yaxis2=dict(
                        title='Number of Invocations',
                        side='right',
                        overlaying='y',
                        showgrid=False
                    ),
                    barmode='group',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Error rate chart
                st.subheader("Error Rate")
                
                # Mock data for visualization - replace with real API data
                error_data = pd.DataFrame({
                    'date': dates,
                    'success': [95, 98, 92, 100, 97, 90, 100, 95, 98, 93, 97, 100, 95, 98],
                    'error': [5, 2, 8, 0, 3, 10, 0, 5, 2, 7, 3, 0, 5, 2]
                })
                
                # Convert to long format for stacked chart
                error_long = pd.melt(
                    error_data, 
                    id_vars=['date'], 
                    value_vars=['success', 'error'],
                    var_name='status', 
                    value_name='percentage'
                )
                
                error_chart = alt.Chart(error_long).mark_area().encode(
                    x='date:T',
                    y=alt.Y('percentage:Q', stack='normalize'),
                    color=alt.Color('status:N', scale=alt.Scale(
                        domain=['success', 'error'],
                        range=['green', 'red']
                    )),
                    tooltip=['date:T', 'status:N', 'percentage:Q']
                ).properties(height=300)
                
                st.altair_chart(error_chart, use_container_width=True)
        else:
            st.info("Select a function to view its metrics")

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("Lambda Function Manager v1.0")
st.sidebar.caption(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
