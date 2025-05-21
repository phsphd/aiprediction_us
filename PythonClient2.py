#!/usr/bin/env python3
"""
Script to debug the fields available in the record and save to JSON file
"""
import requests
import json
import sys
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def save_to_json(data, filename=None):
    """
    Save data to a JSON file with proper formatting
    
    Args:
        data: Data to save (dict or list)
        filename: Optional filename, if None will generate based on DID
    
    Returns:
        The filename that was written to
    """
    if filename is None:
        # Generate filename based on DID if available, otherwise use timestamp
        did = data.get('did', '') if isinstance(data, dict) else ''
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if did:
            filename = f"record_did_{did}_{timestamp}.json"
        else:
            filename = f"records_{timestamp}.json"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Successfully saved data to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to save JSON file: {e}")
        return None

def main():
    # Check command line arguments
    if len(sys.argv) < 3:
        print("Usage: python debug_fields.py username password [did] [api_url] [output_file]")
        sys.exit(1)
        
    username = sys.argv[1]
    password = sys.argv[2]
    did_to_find = int(sys.argv[3]) if len(sys.argv) > 3 else 250520
    api_url = sys.argv[4] if len(sys.argv) > 4 else "http://aiprediction.us"
    output_file = sys.argv[5] if len(sys.argv) > 5 else None
    
    try:
        # Step 1: Get token
        logger.info(f"Authenticating as {username}...")
        auth_data = {"username": username, "password": password}
        
        auth_response = requests.post(f"{api_url}/api-token-auth/", json=auth_data)
        
        if auth_response.status_code != 200:
            logger.error(f"Authentication failed: {auth_response.status_code}")
            logger.error(f"Response: {auth_response.text}")
            sys.exit(1)
        
        # Parse the token
        auth_result = auth_response.json()
        token = auth_result.get("token")
        
        if not token:
            logger.error("No token found in response")
            sys.exit(1)
                
        logger.info(f"Authentication successful. Token: {token[:10]}...")
        
        # Step 2: Get data from the working endpoint
        headers = {"Authorization": f"Token {token}"}
        
        logger.info(f"Fetching data from API ({api_url}/api/v53a/)...")
        list_response = requests.get(f"{api_url}/api/v53a/", headers=headers)
        
        if list_response.status_code != 200:
            logger.error(f"Failed to get data: {list_response.status_code}")
            logger.error(f"Response: {list_response.text}")
            sys.exit(1)
        
        # Process the response
        all_records = list_response.json()
        
        # Save all records to JSON
        all_records_file = save_to_json(all_records, output_file and f"all_{output_file}")
        
        # Check if response is paginated
        if isinstance(all_records, dict) and "results" in all_records:
            all_records = all_records["results"]
            
        logger.info(f"Found {len(all_records)} records")
        
        # Find the record with the specified DID
        target_record = None
        for record in all_records:
            if "did" in record and record["did"] == did_to_find:
                target_record = record
                break
        
        if not target_record:
            logger.error(f"No record found with DID {did_to_find}")
            sys.exit(1)
        
        logger.info(f"Found record with DID {did_to_find}")
        
        # Save the target record to JSON
        saved_file = save_to_json(target_record, output_file)
        
        # DEBUG: Print all available fields in the record
        print("\n=== RECORD STRUCTURE ===")
        
        # Print all the fields in the record and their types
        print("\nFields in the record:")
        for key, value in target_record.items():
            value_type = type(value).__name__
            value_preview = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
            print(f"- {key} ({value_type}): {value_preview}")
        
        # Check for array fields
        print("\nLooking for array fields:")
        expected_fields = ['sp_array', 'es_array', 'p1_array', 'c1_array', 'p2_array', 'c2_array', 
                          'p3_array', 'c3_array', 'p4_array', 'c4_array', 'p5_array', 'c5_array', 
                          'p6_array', 'c6_array', 'p7_array', 'c7_array']
        
        for field in expected_fields:
            if field in target_record:
                value = target_record[field]
                if isinstance(value, list):
                    print(f"- {field}: List with {len(value)} elements")
                    if len(value) > 0:
                        print(f"  First element: {value[0]}")
                        print(f"  Last element: {value[-1]}")
                    else:
                        print(f"  Array is empty")
                else:
                    print(f"- {field}: Not a list, but {type(value).__name__}")
            else:
                print(f"- {field}: Not found in record")
        
        # Try an alternative approach - maybe field names are different
        print("\nSearching for any list fields:")
        for key, value in target_record.items():
            if isinstance(value, list):
                print(f"- {key}: List with {len(value)} elements")
                if len(value) > 0:
                    print(f"  First element: {value[0]}")
                    print(f"  Last element: {value[-1]}")
                else:
                    print(f"  Array is empty")
        
        # Check if 'get_array_field' is a method on the record
        print("\nRaw record data (for debugging):")
        print(json.dumps(target_record, indent=2))
        
        # Print information about saved files
        if saved_file:
            print(f"\nRecord saved to file: {saved_file}")
        if all_records_file:
            print(f"All records saved to file: {all_records_file}")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
