import streamlit as st
import os
import json
import datetime
from generator import generate_samples
from automator import send_to_api
from evaluator import evaluate_and_save

# Must be the first Streamlit command
st.set_page_config(page_title="Email JSON Generator & Automator", layout="wide")

# Title and description
st.title("Email AI Generator & Evaluator")
st.markdown("Generate sample email data, then automate it to AI and evaluate the results.")

# Default API endpoint
DEFAULT_API_ENDPOINT = "https://mlemailintegrationservices-gef9fwepguapgwfr.eastus2-01.azurewebsites.net/test_extraction"

# Initialize session state to track generated files
if 'generated_input_path' not in st.session_state:
    st.session_state.generated_input_path = None
if 'generated_groundtruth_path' not in st.session_state:
    st.session_state.generated_groundtruth_path = None
if 'api_response_path' not in st.session_state:
    st.session_state.api_response_path = None
if 'evaluation_path' not in st.session_state:
    st.session_state.evaluation_path = None
if 'input_json' not in st.session_state:
    st.session_state.input_json = None
if 'groundtruth_json' not in st.session_state:
    st.session_state.groundtruth_json = None
if 'api_response' not in st.session_state:
    st.session_state.api_response = None
if 'evaluation_results' not in st.session_state:
    st.session_state.evaluation_results = None
if 'gemini_api_key' not in st.session_state:
    st.session_state.gemini_api_key = None

# Utility function to create download button
def download_button(file_path, button_text):
    if file_path and os.path.exists(file_path):
        with open(file_path, 'rb') as file:
            return st.download_button(
                label=button_text,
                data=file,
                file_name=os.path.basename(file_path),
                mime='application/json'
            )
    return st.button(f"{button_text} (No file available)", disabled=True)

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    # Gemini API Key Input
    gemini_api_key = st.text_input("Enter Gemini API Key", type="password", 
                                   help="Enter your Gemini API key for generating samples and evaluation.")
    
    # Save API key in session state for later use in evaluation
    if gemini_api_key:
        st.session_state.gemini_api_key = gemini_api_key
    
    # Sentiment Selection
    sentiment = st.radio(
        "Select Email Sentiment",
        ["Positive", "Negative"]
    )
    
    # API Endpoint Input with default value
    api_endpoint = st.text_input(
        "API Endpoint", 
        value=DEFAULT_API_ENDPOINT,
        help="Enter the full URL of your API endpoint"
    )
    
    # Add metrics explanation
    with st.expander("Metrics Explanation"):
        st.markdown("""
        **Precision, Recall, and F1 Score**
        
        These metrics help evaluate how well the AI performs:
        
        - **Precision**: The proportion of correctly identified items among all items identified by the AI
        - **Recall**: The proportion of correctly identified items among all actual items
        - **F1 Score**: The harmonic mean of precision and recall, providing a balanced measure
        
        Perfect scores are 1.0, while 0.0 is the worst possible score.
        """)

# Button columns
col1, col2, col3, col4 = st.columns([1, 1, 1, 0.5])

# Generate button
with col1:
    generate_button = st.button("Generate", type="primary")

# Automate button
with col2:
    automate_button = st.button("Automate", type="primary")

# Evaluate button
with col3:
    evaluate_button = st.button("Evaluate", type="primary")

# Refresh button
with col4:
    # Use st.experimental_rerun() to refresh the page
    refresh_button = st.button("🔄", help="Refresh page to reset state")

# Refresh logic
if refresh_button:
    # Clear relevant session state
    st.session_state.generated_input_path = None
    st.session_state.generated_groundtruth_path = None
    st.session_state.api_response_path = None
    st.session_state.evaluation_path = None
    st.session_state.input_json = None
    st.session_state.groundtruth_json = None
    st.session_state.api_response = None
    st.session_state.evaluation_results = None
    
    # Rerun the app
    st.experimental_rerun()

# Display section for generated files
def display_generated_content():
    """
    Display generated content if available
    """
    # Check if input JSON exists
    if st.session_state.input_json:
        st.markdown("### Generated Files")
        
        # Create columns for file display and downloads
        file_col1, file_col2 = st.columns(2)
        
        with file_col1:
            st.subheader("Input Email JSON")
            st.json(st.session_state.input_json)
            
            # Download Input JSON
            download_button(
                st.session_state.generated_input_path, 
                "Download Input JSON"
            )
        
        with file_col2:
            st.subheader("Output Groundtruth JSON")
            st.json(st.session_state.groundtruth_json)
            
            # Download Groundtruth JSON
            download_button(
                st.session_state.generated_groundtruth_path, 
                "Download Groundtruth JSON"
            )
    
    # Check if API response exists
    if st.session_state.api_response:
        st.markdown("### AI Response")
        
        # Create column for API response
        api_col = st.columns(1)[0]
        
        with api_col:
            st.subheader("AI Service Response")
            st.json(st.session_state.api_response)
            
            # Download API Response
            download_button(
                st.session_state.api_response_path, 
                "Download AI Response"
            )
    
    # Check if evaluation results exist
    if st.session_state.evaluation_results:
        st.markdown("### Evaluation Results (Powered by Gemini AI)")
        
        # Get evaluation results
        eval_results = st.session_state.evaluation_results
        
        # Display overall metrics with colored header
        overall_result = eval_results.get("overall_result", "Failed")
        result_color = "green" if overall_result == "Passed" else "orange" if overall_result == "Partially Passed" else "red"
        
        st.markdown(f"#### Overall Result: <span style='color:{result_color}'>{overall_result}</span>", unsafe_allow_html=True)
        
        # Display metrics in two rows
        st.subheader("Performance Metrics")
        metric_cols1 = st.columns(4)
        with metric_cols1[0]:
            st.metric("Total Keys", eval_results.get("metrics", {}).get("total_keys", 0))
        with metric_cols1[1]:
            st.metric("Passed Keys", eval_results.get("metrics", {}).get("passed_keys", 0))
        with metric_cols1[2]:
            st.metric("Failed Keys", eval_results.get("metrics", {}).get("failed_keys", 0))
        with metric_cols1[3]:
            st.metric("Match %", f"{eval_results.get('metrics', {}).get('match_percentage', 0)}%")
        
        # Add second row for precision, recall, F1
        metric_cols2 = st.columns(3)
        with metric_cols2[0]:
            precision = eval_results.get("metrics", {}).get("precision", 0)
            st.metric("Precision", f"{precision:.2f}")
        with metric_cols2[1]:
            recall = eval_results.get("metrics", {}).get("recall", 0)
            st.metric("Recall", f"{recall:.2f}")
        with metric_cols2[2]:
            f1_score = eval_results.get("metrics", {}).get("f1_score", 0)
            st.metric("F1 Score", f"{f1_score:.2f}")
        
        # Display detailed results
        st.subheader("Detailed Results")
        
        detailed_results = eval_results.get("detailed_results", {})
        
        # Create expandable sections for each key
        for key, result in detailed_results.items():
            status = result.get("status", "Failed")
            status_color = "green" if status == "Passed" else "red"
            
            # Create expander for each key
            with st.expander(f"{key}: <span style='color:{status_color}'>{status}</span>", expanded=False):
                # Display similarity score if available
                if "similarity_score" in result and isinstance(result["similarity_score"], (int, float)):
                    st.progress(float(result["similarity_score"]))
                    st.text(f"Similarity Score: {result['similarity_score']}")
                
                # Display reasoning if available
                if "reasoning" in result:
                    st.markdown("##### Reasoning:")
                    st.write(result["reasoning"])
                
                # Handle Events array specially if it has detailed structure
                if key == "Events" and "event_details" in result:
                    st.markdown("##### Event Details:")
                    for event in result["event_details"]:
                        event_index = event.get("event_index", 0)
                        event_status = event.get("status", "Failed")
                        event_color = "green" if event_status == "Passed" else "red"
                        
                        st.markdown(f"###### Event {event_index + 1}: <span style='color:{event_color}'>{event_status}</span>", unsafe_allow_html=True)
                        
                        # Show field comparisons
                        if "field_comparisons" in event:
                            for field_name, field_result in event["field_comparisons"].items():
                                field_status = field_result.get("status", "Failed")
                                field_color = "green" if field_status == "Passed" else "red"
                                field_similarity = field_result.get("similarity_score", "N/A")
                                
                                st.markdown(f"- {field_name}: <span style='color:{field_color}'>{field_status}</span> (Similarity: {field_similarity})", unsafe_allow_html=True)
        
        # Download Evaluation Results
        download_button(
            st.session_state.evaluation_path, 
            "Download Evaluation Results"
        )

# Handle generation
if generate_button:
    if not gemini_api_key:
        st.error("Please enter a Gemini API key")
    else:
        with st.spinner("Generating JSON Files..."):
            result = generate_samples(
                api_key=gemini_api_key,
                sentiment=sentiment
            )
        
        if result["success"]:
            # Store file paths in session state
            st.session_state.generated_input_path = result["input_path"]
            st.session_state.generated_groundtruth_path = result["output_path"]
            
            # Store JSON data for display
            st.session_state.input_json = result["input_json"]
            st.session_state.groundtruth_json = result["output_json"]
            
            # Reset API response path and evaluation results
            st.session_state.api_response_path = None
            st.session_state.api_response = None
            st.session_state.evaluation_path = None
            st.session_state.evaluation_results = None
            
            # Display success message
            st.success(f"✅ JSON Files generated successfully!")
        else:
            st.error(f"❌ Error: {result['error']}")
            st.info(f"Error details saved to: {result.get('error_path', 'unknown')}")

# Handle API automation
if automate_button:
    # Check prerequisites
    if not st.session_state.generated_input_path:
        st.error("Please generate input JSON first")
    elif not api_endpoint:
        st.error("Please enter an API endpoint")
    else:
        with st.spinner("Sending request to API..."):
            try:
                # Send to API
                api_result = send_to_api(
                    input_file_path=st.session_state.generated_input_path, 
                    api_endpoint=api_endpoint
                )
                
                # Handle API response
                if api_result["success"]:
                    # Store API response path
                    st.session_state.api_response_path = api_result["output_path"]
                    
                    # Store API response for display
                    st.session_state.api_response = api_result["response"]
                    
                    # Reset evaluation results
                    st.session_state.evaluation_path = None
                    st.session_state.evaluation_results = None
                    
                    # Display success
                    st.success("✅ API request successful!")
                    
                    # Show details
                    st.info(f"Response Generated")
                else:
                    st.error(f"❌ API Request Failed: {api_result['error']}")
                    
                    # Show raw response details if available
                    if 'raw_response_path' in api_result:
                        st.info(f"Raw response details saved to: {api_result['raw_response_path']}")
                        
                        # Optional: show raw response text
                        if 'response_text' in api_result:
                            with st.expander("View Raw Response"):
                                st.text(api_result['response_text'])
            
            except Exception as e:
                st.error(f"❌ Unexpected Error: {str(e)}")

# Handle evaluation with Gemini
if evaluate_button:
    # Check prerequisites
    if not st.session_state.generated_groundtruth_path:
        st.error("Please generate groundtruth JSON first")
    elif not st.session_state.api_response_path:
        st.error("Please send request to API first")
    elif not st.session_state.gemini_api_key:
        st.error("Please enter a Gemini API key for evaluation")
    else:
        with st.spinner("Evaluating results with Gemini AI..."):
            try:
                # Evaluate results using Gemini
                eval_result = evaluate_and_save(
                    groundtruth_path=st.session_state.generated_groundtruth_path,
                    ai_response_path=st.session_state.api_response_path,
                    api_key=st.session_state.gemini_api_key
                )
                
                # Handle evaluation result
                if eval_result["success"]:
                    # Store evaluation path
                    st.session_state.evaluation_path = eval_result["output_path"]
                    
                    # Store evaluation results for display
                    st.session_state.evaluation_results = eval_result["results"]
                    
                    # Display success
                    st.success("✅ Evaluation completed successfully!")
                else:
                    st.error(f"❌ Evaluation Failed: {eval_result['error']}")
                    
                    # Show raw response if available
                    if "response_text" in eval_result:
                        with st.expander("View Raw Response"):
                            st.text(eval_result["response_text"])
            
            except Exception as e:
                st.error(f"❌ Unexpected Error: {str(e)}")

# Display generated content
display_generated_content()

# Footer instructions
st.markdown("""
### Workflow Instructions
1. Enter your Gemini API key (used for both generation and evaluation)
2. Select sentiment (Positive/Negative)
3. Click "Generate"
4. (Optional) Enter/Modify API endpoint
5. Click "Automate" to send to API
6. Click "Evaluate" to compare AI response with groundtruth using Gemini
7. Click "Download" to save generated files
""")