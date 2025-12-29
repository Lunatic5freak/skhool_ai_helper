import json
import re
from typing import Optional, Dict, Any, List
from langchain.tools import BaseTool
from langchain_core.callbacks.manager import CallbackManagerForToolRun
from pydantic import Field

from app.database import DatabaseManager
from app.models import SQLQuery


class SchemaLookupTool(BaseTool):
    """Tool for looking up database schema"""
    name: str = "schema_lookup"
    description: str = """
    Useful for looking up database schema information.
    Input can be:
    - A specific table name to get its schema
    - "all" or empty string to get all tables
    - A list of table names separated by commas
    """

    db_manager: DatabaseManager = Field(exclude=True)

    def _run(self, table_names: str = "", run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Look up database schema"""
        try:
            if table_names.lower() in ["all", ""]:
                # Get all tables
                schema = self.db_manager.get_table_schema()
                tables = list(schema.keys())

                # Format response
                response = f"Available tables ({len(tables)}): {', '.join(tables)}\n\n"

                for table_name, table_info in schema.items():
                    columns = table_info['columns']
                    response += f"Table: {table_name}\n"
                    for col in columns[:5]:  # Show first 5 columns
                        response += f"  - {col['name']}: {col['type']}\n"
                    if len(columns) > 5:
                        response += f"  ... and {len(columns) - 5} more columns\n"
                    response += "\n"

                return response
            else:
                # Get specific table(s)
                tables = [t.strip() for t in table_names.split(",") if t.strip()]
                response = ""

                for table_name in tables:
                    try:
                        schema = self.db_manager.get_table_schema(table_name)
                        response += f"Table: {table_name}\n"
                        for col in schema['columns']:
                            pk = " (PK)" if col['pk'] else ""
                            nullable = " (NULL)" if col['notnull'] == 0 else ""
                            response += f"  - {col['name']}: {col['type']}{pk}{nullable}\n"
                        response += "\n"
                    except Exception as e:
                        response += f"Error retrieving schema for table '{table_name}': {str(e)}\n\n"

                return response if response else f"No tables found matching: {table_names}"

        except Exception as e:
            return f"Error looking up schema: {str(e)}"


class QueryExecutorTool(BaseTool):
    """Tool for executing SQL queries"""
    name: str = "query_executor"
    description: str = """
    Useful for executing SQL SELECT queries against the database.
    Input should be a valid SQL SELECT query.
    Important: Only SELECT queries are allowed for security.
    """

    db_manager: DatabaseManager = Field(exclude=True)

    def _run(self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute SQL query"""
        try:
            # Security check - only allow SELECT queries
            query_upper = query.strip().upper()
            if not query_upper.startswith("SELECT"):
                return "Error: Only SELECT queries are allowed for security reasons."

            # Check for dangerous operations
            dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
            for keyword in dangerous_keywords:
                if f" {keyword} " in query_upper or query_upper.endswith(f" {keyword}"):
                    return f"Error: Query contains forbidden keyword: {keyword}"

            # Execute query
            results = self.db_manager.execute_query(query)

            if not results:
                return "Query executed successfully but returned no results."

            # Format results
            if len(results) > 10:
                limited_results = results[:10]
                response = f"Found {len(results)} results (showing first 10):\n\n"
                response += json.dumps(limited_results, indent=2, default=str)
                response += f"\n\n... and {len(results) - 10} more rows"
            else:
                response = f"Found {len(results)} results:\n\n"
                response += json.dumps(results, indent=2, default=str)

            # Add summary statistics
            if results:
                response += f"\n\nSummary: {len(results)} rows returned"
                if 'total_amount' in results[0]:
                    total = sum(float(r.get('total_amount', 0)) for r in results)
                    response += f", Total amount: ${total:,.2f}"

            return response

        except Exception as e:
            return f"Error executing query: {str(e)}"


class SampleDataTool(BaseTool):
    """Tool for getting sample data from tables"""
    name: str = "sample_data"
    description: str = """
    Useful for getting sample data from database tables.
    Input should be a table name and optionally the number of rows (default: 5).
    Format: "table_name, rows" or just "table_name"
    Example: "orders, 3" or "products"
    """

    db_manager: DatabaseManager = Field(exclude=True)

    def _run(self, input_str: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Get sample data from table"""
        try:
            parts = [p.strip() for p in input_str.split(",")]
            table_name = parts[0]
            limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 5

            if limit > 20:  # Safety limit
                limit = 20

            data = self.db_manager.get_sample_data(table_name, limit)

            if not data:
                return f"No data found in table '{table_name}'"

            response = f"Sample data from '{table_name}' ({len(data)} rows):\n\n"
            response += json.dumps(data, indent=2, default=str)

            # Add column information
            if data:
                columns = list(data[0].keys())
                response += f"\n\nColumns: {', '.join(columns)}"

            return response

        except Exception as e:
            return f"Error getting sample data: {str(e)}"


class SQLGeneratorTool(BaseTool):
    """Tool for generating SQL queries from natural language"""
    name: str = "sql_generator"
    description: str = """
    Useful for generating SQL queries from natural language descriptions.
    Input should be a natural language description of what data you want to query.
    Include specific details like table names, filters, sorting, etc.
    Example: "Get all orders for user 1 from last month sorted by date"
    """

    llm_service: Any = Field(exclude=True)

    def _run(self, query_description: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Generate SQL query from natural language"""
        try:
            sql_query = self.llm_service.generate_sql_from_natural_language(query_description, user_id=1)

            response = f"Generated SQL Query:\n```sql\n{sql_query.query}\n```\n\n"

            if sql_query.explanation:
                response += f"Explanation: {sql_query.explanation}\n\n"

            response += "You can execute this query using the query_executor tool."

            return response

        except Exception as e:
            return f"Error generating SQL: {str(e)}"


class DataAnalysisTool(BaseTool):
    """Tool for analyzing query results"""
    name: str = "data_analyzer"
    description: str = """
    After executing a SQL query, use this tool to analyze the results.
    Useful for analyzing query results and providing insights.
    Input should be the query results in JSON format or a description of what to analyze.
    Return only final analysis results. No need to explain your thought process or the steps you took.
    """

    llm_service: Any = Field(exclude=True)

    def _run(self, input_data: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Analyze query results"""
        try:
            # Try to parse as JSON first
            try:
                data = json.loads(input_data)
                if isinstance(data, list):
                    # Analyze the data
                    analysis = self.llm_service.analyze_data(data, "Analyze this data and provide insights")
                    return f"Data Analysis:\n\n{analysis}"
            except json.JSONDecodeError:
                # If not JSON, treat as analysis request
                analysis = self.llm_service.analyze_query_results(input_data)
                return f"Analysis:\n\n{analysis}"

            return "Could not analyze the provided data."

        except Exception as e:
            return f"Error analyzing data: {str(e)}"


class MultiStageQueryPlanner(BaseTool):
    """Tool for planning complex multi-stage queries"""
    name: str = "query_planner"
    description: str = """
    Useful for planning complex queries that require multiple steps.
    Input should be a complex natural language query that might need:
    - Schema lookup first
    - Sample data examination
    - Multiple queries to gather needed information
    - Data aggregation or joining across tables
    """

    db_manager: DatabaseManager = Field(exclude=True)
    llm_service: Any = Field(exclude=True)

    def _run(self, complex_query: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Plan and execute multi-stage query"""
        try:
            # Step 1: Analyze the query
            plan = self.llm_service.create_query_plan(complex_query)

            response = f"Query Plan for: '{complex_query}'\n\n"
            response += "Steps:\n"

            for i, step in enumerate(plan.steps, 1):
                response += f"{i}. {step}\n"

            response += f"\nFinal Query:\n```sql\n{plan.final_query}\n```\n\n"

            # Step 2: Execute the final query
            results = self.db_manager.execute_query(plan.final_query)

            response += f"Results: {len(results)} rows returned\n\n"

            if results:
                # Show sample of results
                sample = results[:3]
                response += "Sample Results:\n"
                response += json.dumps(sample, indent=2, default=str)

                if len(results) > 3:
                    response += f"\n\n... and {len(results) - 3} more rows"

            return response

        except Exception as e:
            return f"Error in multi-stage query planning: {str(e)}"