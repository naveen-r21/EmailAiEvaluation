import requests
import json
import os
import datetime

def send_to_api(input_file_path, api_endpoint):
    """
    Send input JSON file to API and save the response
    
    Args:
        input_file_path (str): Path to the input JSON file
        api_endpoint (str): URL of the API endpoint
    
    Returns:
        dict: Response from the API or error information
    """
    try:
        # Read input JSON file
        with open(input_file_path, 'r', encoding='utf-8') as f:
            request_body = json.load(f)
        
        # Set headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Send request
        response = requests.post(api_endpoint, headers=headers, json=request_body, timeout=30)
        
        # Create output folder if it doesn't exist
        output_folder = "api_responses"
        os.makedirs(output_folder, exist_ok=True)
        
        # Generate timestamp for unique filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw response for debugging
        raw_response_path = os.path.join(output_folder, f"raw_response_{timestamp}.txt")
        with open(raw_response_path, "w", encoding="utf-8") as f:
            f.write(f"API Endpoint: {api_endpoint}\n")
            f.write(f"Status Code: {response.status_code}\n\n")
            f.write(f"Request Headers: {headers}\n\n")
            f.write(f"Request Body:\n{json.dumps(request_body, indent=2)}\n\n")
            f.write(f"Response Headers: {response.headers}\n\n")
            f.write(f"Response Text: {response.text}")
        
        # Try to parse JSON response
        if response.status_code == 200:
            try:
                json_data = response.json()
                
                # Save parsed JSON response
                file_path = os.path.join(output_folder, f"response_output_{timestamp}.json")
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, indent=2)
                
                return {
                    "success": True,
                    "response": json_data,
                    "output_path": file_path,
                    "raw_response_path": raw_response_path
                }
            
            except ValueError:
                return {
                    "success": False,
                    "error": "Response is not valid JSON",
                    "raw_response_path": raw_response_path,
                    "response_text": response.text
                }
        else:
            return {
                "success": False,
                "error": f"HTTP Error {response.status_code}",
                "raw_response_path": raw_response_path,
                "response_text": response.text
            }
    
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }

# If script is run directly (for testing)
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2:
        input_file = sys.argv[1]
        api_endpoint = sys.argv[2]
        result = send_to_api(input_file, api_endpoint)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python automator.py <INPUT_JSON_PATH> <API_ENDPOINT>")