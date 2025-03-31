#!/usr/bin/env python3
"""
Tests for the server functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
from fastapi.testclient import TestClient
import sys
import os

# Add the parent directory to the path so we can import the server module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import server

class TestServer(unittest.TestCase):
    """Test the server functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = TestClient(server.app)
        
    def test_get_info(self):
        """Test the info endpoint."""
        response = self.client.get("/info")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Synapse MCP Server")
        self.assertIn("version", data)
        
    def test_list_tools(self):
        """Test the tools endpoint."""
        response = self.client.get("/tools")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        
    def test_list_resources(self):
        """Test the resources endpoint."""
        response = self.client.get("/resources")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        
    @patch('server.get_datasets_as_croissant')
    def test_get_datasets_as_croissant(self, mock_get_datasets):
        """Test the Croissant datasets endpoint."""
        # Setup mock
        mock_data = {
            "@context": ["https://schema.org/", {"csv": "http://www.w3.org/ns/csvw#", "dc": "http://purl.org/dc/elements/1.1/"}],
            "@type": "Dataset", 
            "dataset": []  # We only check for the existence of the dataset key, not its exact content
        }
        mock_get_datasets.return_value = mock_data
        
        # Call the endpoint
        response = self.client.get("/resources/croissant/datasets")
        
        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["@context"], mock_data["@context"])
        self.assertEqual(data["@type"], mock_data["@type"])
        self.assertIn("dataset", data)
        mock_get_datasets.assert_called_once()
        
    @patch('server.authenticate')
    def test_authenticate(self, mock_authenticate):
        """Test the authenticate endpoint."""
        # Setup mock
        mock_authenticate.return_value = {"success": True}
        
        # Call the endpoint
        response = self.client.post(
            "/tools/authenticate",
            json={"auth_token": "fake_token"}
        )
        
        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, {"success": True})
        mock_authenticate.assert_called_once_with(auth_token="fake_token")
        
    @patch('server.query_table')
    def test_query_table(self, mock_query_table):
        """Test the query_table endpoint."""
        # Setup mock
        mock_result = {
            "headers": ["col1", "col2"],
            "data": [["val1", "val2"]]
        }
        mock_query_table.return_value = mock_result
        
        # Call the endpoint
        response = self.client.post(
            "/tools/query_table",
            json={"table_id": "syn123", "query": "SELECT * FROM syn123"}
        )
        
        # Assert
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, mock_result)
        mock_query_table.assert_called_once_with(table_id="syn123", query="SELECT * FROM syn123")

if __name__ == "__main__":
    unittest.main()