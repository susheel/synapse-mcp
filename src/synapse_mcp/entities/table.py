import synapseclient
from typing import Dict, List, Any, Optional, Union

from .base import BaseEntityOperations

class TableOperations(BaseEntityOperations):
    """Operations for Synapse Table entities."""
    
    def get_table_columns(self, table_id: str) -> List[Dict[str, Any]]:
        """Get columns for a table.
        
        Args:
            table_id: The Synapse ID of the table
            
        Returns:
            List of column definitions
        """
        # Get table columns from Synapse
        columns = self.synapse_client.getTableColumns(table_id)
        return [self._format_column(col) for col in columns]
    
    def query_table(self, table_id: str, query: str) -> Dict[str, Any]:
        """Query a table with SQL-like syntax.
        
        Args:
            table_id: The Synapse ID of the table
            query: SQL-like query string
            
        Returns:
            Query results
        """
        # If query doesn't start with SELECT, add a basic select
        if not query.strip().upper().startswith('SELECT'):
            query = f"SELECT * FROM {table_id} {query}"
        # If query doesn't include FROM clause, add it
        elif 'FROM' not in query.upper():
            query = f"{query} FROM {table_id}"
        
        try:
            # Execute the query
            query_result = self.synapse_client.tableQuery(query)
            
            # Convert to DataFrame for consistent handling
            df = query_result.asDataFrame()
            
            # Convert DataFrame to a dictionary format
            result = {
                'headers': df.columns.tolist(),
                'data': df.values.tolist()
            }
            
            return result
        except Exception as e:
            # Return error information if query fails
            return {
                'error': str(e),
                'query': query
            }
    
    def _format_column(self, column: Any) -> Dict[str, Any]:
        """Format a column definition as a dictionary.
        
        Args:
            column: The column definition
            
        Returns:
            Column definition as a dictionary
        """
        return {
            'id': column.get('id') if hasattr(column, 'get') else getattr(column, 'id', None),
            'name': column.get('name') if hasattr(column, 'get') else getattr(column, 'name', None),
            'columnType': column.get('columnType') if hasattr(column, 'get') else getattr(column, 'columnType', None),
            'maximumSize': column.get('maximumSize') if hasattr(column, 'get') else getattr(column, 'maximumSize', None),
            'defaultValue': column.get('defaultValue') if hasattr(column, 'get') else getattr(column, 'defaultValue', None),
        }