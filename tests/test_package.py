import unittest
from synapse_mcp.entities.croissant import convert_to_croissant


import importlib.util
import os
import sys

class TestPackageInstallation(unittest.TestCase):
    """Test the synapse-mcp package installation."""

    def test_package_imports(self):
        """Test that all package modules can be imported."""
        # Test main package import
        import synapse_mcp
        self.assertIsNotNone(synapse_mcp)
        
        # Test submodules
        from synapse_mcp import auth
        self.assertTrue(auth is None or hasattr(auth, "authorize"))
        
        from synapse_mcp import query
        self.assertIsNotNone(query)
        
        from synapse_mcp import utils
        self.assertIsNotNone(utils)
        
        from synapse_mcp.entities import croissant
        self.assertIsNotNone(croissant)
        
        # Test entities subpackage
        from synapse_mcp.entities import base
        self.assertIsNotNone(base)
        
        from synapse_mcp.entities import table
        self.assertIsNotNone(table)
        
        from synapse_mcp.entities import dataset
        self.assertIsNotNone(dataset)
        
        from synapse_mcp.entities import file
        self.assertIsNotNone(file)
        
        from synapse_mcp.entities import folder
        self.assertIsNotNone(folder)
        
        from synapse_mcp.entities import project
        self.assertIsNotNone(project)

    def test_entry_point(self):
        """Test that the entry point is available."""
        # Check if the main module has a main function
        from synapse_mcp.__main__ import main
        self.assertTrue(callable(main))

if __name__ == "__main__":
    unittest.main()
