#!/usr/bin/env python3
"""
Tests for the authentication functionality.
"""

import unittest
from unittest.mock import MagicMock, patch
from synapse_mcp.auth import SynapseAuth

class TestSynapseAuth(unittest.TestCase):
    """Test the Synapse authentication functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.auth = SynapseAuth()
        
    @patch('synapseclient.Synapse')
    def test_authenticate_with_token(self, mock_synapse):
        """Test authentication with a token."""
        # Setup mock
        mock_instance = MagicMock()
        mock_synapse.return_value = mock_instance
        
        # Call the method
        self.auth.authenticate(auth_token="fake_token")
        
        # Assert
        mock_instance.login.assert_called_once_with(authToken="fake_token")
        self.assertIsNotNone(self.auth.synapse_client)
        
    @patch('synapseclient.Synapse')
    def test_authenticate_without_token(self, mock_synapse):
        """Test authentication without a token."""
        # Setup mock
        mock_instance = MagicMock()
        mock_synapse.return_value = mock_instance
        
        # Call the method and assert it raises
        with self.assertRaises(ValueError):
            self.auth.authenticate(auth_token=None)
            
    @patch('synapseclient.Synapse')
    def test_get_client_authenticated(self, mock_synapse):
        """Test getting client when authenticated."""
        # Setup mock
        mock_instance = MagicMock()
        mock_synapse.return_value = mock_instance
        
        # Authenticate
        self.auth.authenticate(auth_token="fake_token")
        
        # Get client
        client = self.auth.get_client()
        
        # Assert
        self.assertEqual(client, mock_instance)
        mock_instance.getUserProfile.assert_called_once()
        
    def test_get_client_not_authenticated(self):
        """Test getting client when not authenticated."""
        # Call the method and assert it raises
        with self.assertRaises(RuntimeError):
            self.auth.get_client()
            
    @patch('synapseclient.Synapse')
    def test_is_authenticated_true(self, mock_synapse):
        """Test is_authenticated when authenticated."""
        # Setup mock
        mock_instance = MagicMock()
        mock_synapse.return_value = mock_instance
        
        # Authenticate
        self.auth.authenticate(auth_token="fake_token")
        
        # Check authentication
        is_auth = self.auth.is_authenticated()
        
        # Assert
        self.assertTrue(is_auth)
        mock_instance.getUserProfile.assert_called_once()
        
    @patch('synapseclient.Synapse')
    def test_is_authenticated_false_exception(self, mock_synapse):
        """Test is_authenticated when getUserProfile raises exception."""
        # Setup mock
        mock_instance = MagicMock()
        mock_instance.getUserProfile.side_effect = Exception("Not authenticated")
        mock_synapse.return_value = mock_instance
        
        # Authenticate
        self.auth.authenticate(auth_token="fake_token")
        
        # Check authentication
        is_auth = self.auth.is_authenticated()
        
        # Assert
        self.assertFalse(is_auth)
        mock_instance.getUserProfile.assert_called_once()
        
    def test_is_authenticated_false_no_client(self):
        """Test is_authenticated when no client."""
        # Check authentication
        is_auth = self.auth.is_authenticated()
        
        # Assert
        self.assertFalse(is_auth)

if __name__ == "__main__":
    unittest.main()