#!/usr/bin/env python3
"""
Tests for the Croissant metadata conversion functionality.
"""

import unittest
from synapse_mcp.entities.croissant import (
    convert_to_croissant,
    create_dataset_entry,
    get_value_or_default
)

class TestCroissantConversion(unittest.TestCase):
    """Test the Croissant metadata conversion functionality."""

    def test_get_value_or_default(self):
        """Test the get_value_or_default function."""
        # Test with existing key
        test_dict = {"key1": "value1", "key2": None}
        self.assertEqual(get_value_or_default(test_dict, "key1"), "value1")
        
        # Test with missing key
        self.assertEqual(get_value_or_default(test_dict, "key3"), None)
        self.assertEqual(get_value_or_default(test_dict, "key3", "default"), "default")
        
        # Test with None value
        self.assertEqual(get_value_or_default(test_dict, "key2"), None)
        self.assertEqual(get_value_or_default(test_dict, "key2", "default"), "default")

    def test_create_dataset_entry(self):
        """Test the create_dataset_entry function."""
        # Test with valid data
        test_row = {
            "id": "syn12345678",
            "title": "Test Dataset",
            "description": "A test dataset",
            "diseaseFocus": "Neuroscience",
            "dataType": "Genomics",
            "yearProcessed": "2023",
            "fundingAgency": "NIH"
        }
        
        entry = create_dataset_entry(test_row)
        self.assertIsNotNone(entry)
        
        if entry is not None:  # Add this check to avoid pylance errors
            self.assertEqual(entry["@type"], "Dataset")
            self.assertEqual(entry["@id"], "https://www.synapse.org/#!Synapse:syn12345678")
            self.assertEqual(entry["name"], "Test Dataset")
            self.assertEqual(entry["description"], "A test dataset")
            self.assertEqual(entry["keywords"], ["Neuroscience"])
            self.assertEqual(entry["measurementTechnique"], "Genomics")
            self.assertEqual(entry["temporalCoverage"], "2023")
            self.assertEqual(entry["funder"]["name"], "NIH")
        
        # Test with missing required fields
        test_row_missing = {
            "description": "A test dataset"
        }
        
        entry_missing = create_dataset_entry(test_row_missing)
        self.assertIsNone(entry_missing)

    def test_convert_to_croissant(self):
        """Test the convert_to_croissant function."""
        # Test with valid data
        test_data = {
            "headers": ["id", "title", "description", "diseaseFocus", "dataType", "yearProcessed", "fundingAgency"],
            "data": [
                ["syn12345678", "Test Dataset", "A test dataset", "Neuroscience", "Genomics", "2023", "NIH"]
            ]
        }
        
        result = convert_to_croissant(test_data)
        self.assertIsNotNone(result)
        self.assertEqual(result["@type"], "Dataset")
        self.assertEqual(result["name"], "Sage Bionetworks Public Datasets")
        self.assertEqual(len(result["dataset"]), 1)
        self.assertEqual(result["dataset"][0]["@id"], "https://www.synapse.org/#!Synapse:syn12345678")
        self.assertEqual(result["dataset"][0]["name"], "Test Dataset")
        
        # Test with empty data
        test_empty = {
            "headers": [],
            "data": []
        }
        
        result_empty = convert_to_croissant(test_empty)
        self.assertIsNotNone(result_empty)
        self.assertEqual(len(result_empty["dataset"]), 0)

if __name__ == "__main__":
    unittest.main()