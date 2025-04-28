import json
import os
import datetime
import google.generativeai as genai

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

def evaluate_with_gemini(api_key, groundtruth_json, ai_response_json):
    """
    Use Gemini AI to evaluate AI response against groundtruth
    
    Args:
        api_key (str): Gemini API key
        groundtruth_json (dict): The groundtruth JSON
        ai_response_json (dict): The AI response JSON
    
    Returns:
        dict: Evaluation results
    """
    # First, validate the API configuration
    api_valid, api_error = configure_gemini_api(api_key)
    if not api_valid:
        return {
            "success": False,
            "error": api_error or "API configuration failed"
        }
    
    # Create model with specific parameters for consistency
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={
            "temperature": 0.1,  # Low temperature for consistency
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
    )
    
    # Get groundtruth JSON
    gt_json = groundtruth_json.get("groundtruth_json", groundtruth_json)
    
    # Create the JSON portions as separate strings to avoid nested f-string issues
    gt_json_str = json.dumps(gt_json, indent=2)
    ai_json_str = json.dumps(ai_response_json, indent=2)
    
    # Define the output format in a separate string to avoid nesting issues
    output_format = '''
    {
      "overall_result": "Passed or Failed or Partially Passed",
      "metrics": {
        "total_keys": number of keys evaluated,
        "passed_keys": number of keys that passed,
        "failed_keys": number of keys that failed,
        "match_percentage": percentage of passed keys
      },
      "detailed_results": {
        "key_name1": {
          "status": "Passed or Failed",
          "similarity_score": 0.0-1.0,
          "reasoning": "Why this passed or failed"
        },
        "key_name2": {
          "status": "Passed or Failed", 
          "similarity_score": 0.0-1.0,
          "reasoning": "Why this passed or failed"
        },
        "Events": {
          "status": "Passed or Failed",
          "reasoning": "Overall assessment of events matching",
          "event_details": [
            {
              "event_index": 0,
              "status": "Passed or Failed",
              "field_comparisons": {
                "Event name": {"status": "Passed or Failed", "similarity_score": 0.0-1.0},
                "Date": {"status": "Passed or Failed", "similarity_score": 0.0-1.0},
                "Time": {"status": "Passed or Failed", "similarity_score": 0.0-1.0},
                "Property Type": {"status": "Passed or Failed", "similarity_score": 0.0-1.0},
                "Agent Name": {"status": "Passed or Failed", "similarity_score": 0.0-1.0},
                "Location": {"status": "Passed or Failed", "similarity_score": 0.0-1.0}
              }
            }
          ]
        }
      }
    }
    '''
    
    # Prepare prompt for Gemini - combining the parts without nesting f-strings
    prompt = """
    Task: Evaluate how well an AI system extracted information from an email by comparing the AI response to the ground truth.

    Ground Truth JSON:
    ```json
    """ + gt_json_str + """
    ```

    AI Response JSON:
    ```json
    """ + ai_json_str + """
    ```

    Instructions:
    1. Analyze each key in the Ground Truth JSON and compare it with the corresponding key in the AI Response.
    2. For each key, determine if it's a PASS or FAIL based on semantic equivalence (meaning is the same even if wording differs).
    3. For text fields, assign a similarity score from 0.0 to 1.0.
    4. For structured data like lists or nested objects, evaluate their contents.
    5. Provide detailed reasoning for each evaluation decision.

    Output Format Requirements:
    Provide your evaluation in JSON format with the following structure:
    ```json
    """ + output_format + """
    ```

    Important notes:
    - A key passes if the semantic meaning matches, even if the wording is different.
    - For identifiers like mail_id and thread_id, an exact match is required.
    - For "Sentiment analysis" and "overall_sentiment_analysis", exact matches are required.
    - For "Summary", evaluate if the AI captured the main points of the email correctly.
    - For "Events", check if all required fields are correctly extracted.
    - A "Partially Passed" overall result should be given if at least 80% of keys pass.
    """
    
    try:
        # Generate evaluation from Gemini
        response = model.generate_content(prompt)
        
        # Parse JSON from the response
        eval_response_text = response.text
        
        # Try to extract JSON from the response
        json_matches = []
        
        # Try to find JSON within code blocks
        import re
        json_matches = re.findall(r'```json\n(.*?)\n```', eval_response_text, re.DOTALL)
        
        if json_matches:
            # Use the first JSON block found
            eval_results = json.loads(json_matches[0])
        else:
            # If no JSON code blocks, try to parse the entire response
            try:
                eval_results = json.loads(eval_response_text)
            except:
                # Last resort: try to find anything between braces
                json_text = re.search(r'\{.*\}', eval_response_text, re.DOTALL)
                if json_text:
                    eval_results = json.loads(json_text.group(0))
                else:
                    raise ValueError("Could not extract JSON from Gemini response")
        
        # Add evaluation timestamp
        eval_results["evaluation_timestamp"] = datetime.datetime.now().isoformat()
        
        # Calculate precision, recall, and F1 score
        metrics = calculate_metrics(eval_results)
        eval_results["metrics"].update(metrics)
        
        return {
            "success": True,
            "results": eval_results
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Evaluation failed: {str(e)}",
            "response_text": response.text if 'response' in locals() else "No response generated"
        }

def calculate_metrics(eval_results):
    """
    Calculate precision, recall, and F1 score based on evaluation results
    
    Args:
        eval_results (dict): Evaluation results from Gemini
    
    Returns:
        dict: Precision, recall, and F1 score metrics
    """
    metrics = {}
    
    # Extract counts from the evaluation results
    total_keys = eval_results["metrics"]["total_keys"]
    passed_keys = eval_results["metrics"]["passed_keys"]
    failed_keys = eval_results["metrics"]["failed_keys"]
    
    # Define true positives, false positives, and false negatives
    # True positives: keys that passed evaluation
    true_positives = passed_keys
    
    # False positives: keys that should have failed but passed (we don't have this info)
    # False negatives: keys that should have passed but failed
    false_negatives = failed_keys
    
    # Calculate precision, recall, and F1 score
    # Since we don't have true false positives in this scenario,
    # precision is always 1.0 (all passed keys are correct by definition)
    precision = 1.0
    
    # Recall is the proportion of true positives to all actual positives
    recall = true_positives / total_keys if total_keys > 0 else 0
    
    # F1 score is the harmonic mean of precision and recall
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    # Add metrics to the result
    metrics["precision"] = round(precision, 2)
    metrics["recall"] = round(recall, 2)
    metrics["f1_score"] = round(f1_score, 2)
    
    return metrics

def evaluate_and_save(groundtruth_path, ai_response_path, api_key):
    """
    Evaluate JSON files using Gemini and save results
    
    Args:
        groundtruth_path (str): Path to groundtruth JSON file
        ai_response_path (str): Path to AI response JSON file
        api_key (str): Gemini API key
    
    Returns:
        dict: Results including success status and output path
    """
    try:
        # Create evaluation results directory
        output_dir = "evaluation_results"
        os.makedirs(output_dir, exist_ok=True)
        
        # Read JSON files
        with open(groundtruth_path, 'r', encoding='utf-8') as f:
            groundtruth_json = json.load(f)
        
        with open(ai_response_path, 'r', encoding='utf-8') as f:
            ai_response_json = json.load(f)
        
        # Perform evaluation with Gemini
        evaluation_result = evaluate_with_gemini(
            api_key=api_key,
            groundtruth_json=groundtruth_json,
            ai_response_json=ai_response_json
        )
        
        if not evaluation_result["success"]:
            return evaluation_result
        
        evaluation_results = evaluation_result["results"]
        
        # Generate filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"gemini_evaluation_{timestamp}.json")
        
        # Save evaluation results
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(evaluation_results, f, indent=2)
        
        return {
            "success": True,
            "results": evaluation_results,
            "output_path": output_path
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# If script is run directly (for testing)
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 3:
        groundtruth_path = sys.argv[1]
        ai_response_path = sys.argv[2]
        api_key = sys.argv[3]
        
        result = evaluate_and_save(groundtruth_path, ai_response_path, api_key)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python evaluator.py <GROUNDTRUTH_JSON_PATH> <AI_RESPONSE_JSON_PATH> <GEMINI_API_KEY>")