#!/usr/bin/env python3
"""
Simple server to test the Croissant functionality.
"""

from fastapi import FastAPI
import uvicorn
from src.synapse_mcp import convert_to_croissant

app = FastAPI(title="Croissant Test Server")

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the Croissant Test Server"}

@app.get("/croissant/datasets")
async def get_datasets_as_croissant():
    """Get public datasets in Croissant metadata format."""
    # Create a sample dataset structure for demonstration
    sample_data = {
        'headers': ['id', 'title', 'description', 'diseaseFocus', 'dataType', 'yearProcessed', 'fundingAgency'],
        'data': [
            ['syn12345678', 'Sample Dataset', 'A sample dataset for demonstration', 'Neuroscience', 'Genomics', '2023', 'NIH'],
            ['syn87654321', 'Another Dataset', 'Another sample dataset', 'Cancer', 'Proteomics', '2024', 'NCI']
        ]
    }
    
    # Convert to Croissant format
    croissant_data = convert_to_croissant(sample_data)
    
    return croissant_data

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)