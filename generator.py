# generator.py
import streamlit as st
import google.generativeai as genai
import os
import json
import datetime
import re
import html
import uuid

# Function to validate and configure Gemini API
def configure_gemini_api(api_key):
    """
    Configure Gemini API with error handling
    
    Args:
        api_key (str): Gemini API key
    
    Returns:
        tuple: (success_boolean, error_message_or_None)
    """
    try:
        # Remove any leading/trailing whitespace
        api_key = api_key.strip()
        
        # Basic validation
        if not api_key:
            return False, "API key cannot be empty"
        
        # Configure the API
        genai.configure(api_key=api_key)
        
        # Test the configuration with a simple generation
        model = genai.GenerativeModel('gemini-1.5-flash')
        test_response = model.generate_content("Hello, can you confirm the API is working?", 
                                               generation_config={
                                                   "temperature": 0.1,
                                                   "max_output_tokens": 50
                                               })
        
        # If we reach here, the API is working
        return True, None
    
    except Exception as e:
        # Capture and return any configuration or generation errors
        error_msg = str(e)
        
        # Provide more user-friendly error messages
        if "429" in error_msg:
            error_msg = "API rate limit exceeded. Please try again later."
        elif "401" in error_msg:
            error_msg = "Invalid API key. Please check your credentials."
        
        return False, error_msg

# Function to generate samples
def generate_samples(api_key, sentiment):
    """
    Generate sample JSON files using Gemini AI
    
    Args:
        api_key (str): Gemini API key
        sentiment (str): Email sentiment (Positive/Negative)
    
    Returns:
        dict: Generation result with success status, generated files, etc.
    """
    try:
        # First, validate the API configuration
        api_valid, api_error = configure_gemini_api(api_key)
        if not api_valid:
            return {
                "success": False,
                "error": api_error or "API configuration failed"
            }
        
        # Create model with more specific parameters for consistency
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 0.2,  # Low temperature for consistency
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
        )
        
        # Customize prompt based on sentiment
        sentiment_value = "green" if sentiment == "Positive" else "red"
        sentiment_text = "positive" if sentiment == "Positive" else "negative"
        
        # Detailed prompt for full JSON generation
        prompt = f"""
        Generate a comprehensive JSON for an email exchange in a relocation services scenario.
        
        Key Requirements:
        - Create realistic email data for a {sentiment_text} relocation service interaction
        - Ensure all JSON fields are populated with contextually appropriate information
        - Use a {sentiment_text} tone throughout the email content
        
        Detailed JSON Structure Instructions:
        1. input_json should include:
           - Unique mail_id and thread_id
           - Realistic sender email
           - Current timestamp
           - Full email body with professional formatting
        
        2. groundtruth_json should include:
           - Sentiment analysis
           - Feature name
           - Event details
           - Comprehensive summary
        
        JSON Template:
        {{
          "input_json": {{
            "mail_id": "unique alphanumeric identifier",
            "file_name": [],
            "email": "professional email address ",
            "mail_time": "ISO8601 timestamp",
            "body_type": "html",(always html)
            "mail_body":  "Complete email content with professional greeting, body, and signature", (plain text and no html tags, including Agent [name], greeting with employee name [random name] and signature with sender name which is same as mail address, add city name and furnished or unfurnished) [generate new body everytime with some of the options i mentioned ]
            "thread_id": "unique thread identifier",
            "mail_summary": "Concise email summary"
          }},
          "groundtruth_json": {{
            "Sentiment analysis": "{sentiment_value}",
            "overall_sentiment_analysis": "{sentiment_text}",
            "feature": "Specific relocation service feature",
            "category": "Initial Service Milestones",
            "Summary": "Comprehensive email summary capturing key points",
            "Events": [
              {{
                "Event name": "Specific service event",(fetch from email body)
                "Date": " YYYY-MM-DD format", (if mentioned in email body)
                "Time": "Event time in HH:MM PM/AM format", (if mentioned in email body)
                "Property Type": "Furnished/Unfurnished/null", (if mentioned in email body)
                "Agent Name": "agent name",(if mentioned in email body as Agent [name])
                "Location": "Specific city name" (if mentioned in email body)
              }}
            ],
            "mail_id": "matching input mail_id",
            "thread_id": "matching input thread_id"
          }}
        }}
        
        Important Notes:
        - Ensure perfect JSON formatting
        - Provide realistic, professional content
        - Match mail_id and thread_id across both JSON objects
        - Create a coherent narrative in the email
        """
        
        # Generate response from Gemini
        response = model.generate_content(prompt)
        
        # Extract and parse JSON
        def extract_json(text):
            # Find JSON within code blocks or between braces
            json_matches = re.findall(r'```json\n(.*?)```|\{.*?\}', text, re.DOTALL | re.MULTILINE)
            
            # Try parsing each match
            for match in json_matches:
                try:
                    # Remove any leading/trailing whitespace
                    cleaned_match = match.strip()
                    parsed_json = json.loads(cleaned_match)
                    
                    # Validate the structure
                    if 'input_json' in parsed_json and 'groundtruth_json' in parsed_json:
                        return parsed_json
                except (json.JSONDecodeError, KeyError):
                    continue
            
            # If no valid JSON found, raise an exception
            raise ValueError("Could not extract valid JSON from response")
        
        # Parse the full JSON
        full_data = extract_json(response.text)
        
        # Unpack the JSONs
        input_json = full_data['input_json']
        groundtruth_json = full_data['groundtruth_json']
        
        # Save to files
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Ensure samples directory exists
        os.makedirs("samples", exist_ok=True)
        
        input_file_path = f"samples/sample_input_{timestamp}.json"
        output_file_path = f"samples/sample_groundtruth_{timestamp}.json"
        
        # Write input JSON
        with open(input_file_path, "w", encoding="utf-8") as f:
            json.dump(input_json, f, indent=2)
        
        # Write groundtruth JSON
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(groundtruth_json, f, indent=2)
        
        return {
            "success": True,
            "input_json": input_json,
            "output_json": groundtruth_json,
            "input_path": input_file_path,
            "output_path": output_file_path
        }
    
    except Exception as e:
        # On failure, save error info
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        error_file_path = f"samples/error_output_{timestamp}.txt"
        
        os.makedirs("samples", exist_ok=True)
        
        with open(error_file_path, "w", encoding="utf-8") as f:
            f.write(f"// Failed to generate or parse JSON. Error details below:\n\n")
            f.write(f"ERROR: {str(e)}\n\n")
            f.write(f"FULL RESPONSE:\n{response.text}")
        
        return {
            "success": False,
            "error": str(e),
            "error_path": error_file_path
        }

# Optional: If this script is run directly
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2:
        api_key = sys.argv[1]
        sentiment = sys.argv[2]
        result = generate_samples(api_key, sentiment)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python generator.py <API_KEY> <SENTIMENT>")