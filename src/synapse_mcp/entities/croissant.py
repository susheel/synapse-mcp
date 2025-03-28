"""
Utilities for converting Synapse datasets to Croissant metadata format.
"""
import json
from typing import Dict, List, Any, Optional
import datetime

def convert_to_croissant(table_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Synapse table data to Croissant metadata format.
    
    Args:
        table_data: Table data from Synapse query
        
    Returns:
        Croissant metadata as a dictionary
    """
    # Extract headers and data from table_data
    headers = table_data.get('headers', [])
    data = table_data.get('data', [])
    
    # Initialize Croissant metadata structure
    croissant_metadata = {
        "@context": [
            "https://schema.org/",
            {
                "csv": "http://www.w3.org/ns/csvw#",
                "dc": "http://purl.org/dc/elements/1.1/"
            }
        ],
        "@type": "Dataset",
        "name": "Sage Bionetworks Public Datasets",
        "description": "Collection of public datasets from Sage Bionetworks",
        "url": f"https://www.synapse.org/#!Synapse:syn61609402",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "isAccessibleForFree": True,
        "datePublished": datetime.datetime.now().strftime('%Y-%m-%d'),
        "distribution": {
            "@type": "DataDownload",
            "contentUrl": f"https://www.synapse.org/#!Synapse:syn61609402",
            "encodingFormat": "application/json"
        },
        "creator": {
            "@type": "Organization",
            "name": "Sage Bionetworks",
            "url": "https://sagebionetworks.org/"
        },
        "dataset": []
    }
    
    # Process each row to create individual dataset entries
    for row_data in data:
        # Create a dictionary from headers and row data
        row = {headers[i]: row_data[i] for i in range(len(headers)) if i < len(row_data)}
        dataset_entry = create_dataset_entry(row)
        if dataset_entry:
            croissant_metadata["dataset"].append(dataset_entry)
    
    return croissant_metadata

def create_dataset_entry(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create a Croissant dataset entry from a row in the table.
    
    Args:
        row: A row from the datasets table as a dictionary
        
    Returns:
        Dataset entry in Croissant format, or None if invalid
    """
    # Extract required fields
    dataset_id = get_value_or_default(row, 'id')
    title = get_value_or_default(row, 'title')
    
    if not dataset_id or not title:
        return None
    
    # Create the dataset entry
    entry = {
        "@type": "Dataset",
        "@id": f"https://www.synapse.org/#!Synapse:{dataset_id}",
        "name": title,
        "description": get_value_or_default(row, 'description', "No description available"),
        "keywords": get_value_or_default(row, 'diseaseFocus', "").split(",") if get_value_or_default(row, 'diseaseFocus') else [],
        "measurementTechnique": get_value_or_default(row, 'dataType', "Not specified"),
        "temporalCoverage": get_value_or_default(row, 'yearProcessed', ""),
    }
    
    # Add funding information if available
    funding = get_value_or_default(row, 'fundingAgency')
    if funding:
        entry["funder"] = {
            "@type": "Organization",
            "name": funding
        }
    
    # Add data access information
    entry["conditionsOfAccess"] = "https://sagebionetworks.org/tools_resources/data-use-agreements/"
    
    return entry

def get_value_or_default(row: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Get a value from a dictionary, handling missing keys and None values.
    
    Args:
        row: The dictionary to get the value from
        key: The key to get
        default: The default value to return if the key is missing or the value is None
        
    Returns:
        The value or the default
    """
    try:
        value = row[key]
        if value is None:
            return default
        return value
    except (KeyError, TypeError):
        return default