#!/usr/bin/env python3
"""
Example script to demonstrate using the Croissant metadata endpoint.
"""

import requests
import json
import sys
import os

# Server URL
SERVER_URL = "http://127.0.0.1:9000"

def get_datasets_as_croissant():
    """Get public datasets in Croissant metadata format."""
    # Call the resource endpoint
    response = requests.get(f"{SERVER_URL}/resources/croissant/datasets")
    
    print(f"Response status code: {response.status_code}")
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        print("Full response:", response.content)
        return None
    
    return response.json()

def save_croissant_metadata(data, output_file="croissant_metadata.json"):
    """Save Croissant metadata to a file."""
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved Croissant metadata to {output_file}")

def main():
    """Main function."""
    print("Fetching public datasets in Croissant format...")
    
    # Get datasets in Croissant format
    croissant_data = get_datasets_as_croissant()
    
    if not croissant_data:
        print("Failed to get datasets in Croissant format.")
        sys.exit(1)
    
    # Check if there was an error
    if "error" in croissant_data:
        print("Full response:", croissant_data)
        print(f"Error: {croissant_data['error']}")
        if "message" in croissant_data:
            print(f"Message: {croissant_data['message']}")
        sys.exit(1)
    
    # Print summary
    dataset_count = len(croissant_data.get("dataset", []))
    print(f"Retrieved {dataset_count} datasets in Croissant format.")
    
    # Save to file
    save_croissant_metadata(croissant_data)
    
    # Print a sample of the data
    print("\nSample of Croissant metadata:")
    print(json.dumps(croissant_data, indent=2)[:500] + "...\n")

if __name__ == "__main__":
    main()