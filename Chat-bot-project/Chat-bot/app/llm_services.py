import os
import json
import logging
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from app.models import SQLQuery, QueryPlan
from app.database import DatabaseManager

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, db_manager: DatabaseManager):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.llm = ChatOpenAI(
            model=self.model,
            temperature=0.1,
            api_key=self.api_key
        )

        # Create SQLDatabase connection for LangChain
        self.db = SQLDatabase.from_uri("sqlite:///chatbot.db")
        self.db_manager = db_manager

        logger.info(f"LLM Service initialized with model: {self.model}")

    def generate_sql_from_natural_language(self, user_query: str, user_id: int = 1) -> SQLQuery:
        """Generate SQL query from natural language using LangChain"""

        # Get database schema
        schema = self.db.get_table_info()

        prompt = PromptTemplate.from_template("""
        You are an expert SQL assistant. Given the following database schema and user query, generate a SQLite SQL query.

        Database Schema:
        {schema}

        User ID: {user_id}
        User Query: {query}

        Important Guidelines:
        1. Only generate SELECT queries (read-only)
        2. When querying user-specific data (orders, payments), include WHERE user_id = {user_id}
        3. Use parameterized queries with ? placeholders
        4. Include LIMIT clause for safety (default LIMIT 50)
        5. Use proper joins when needed
        6. Format dates appropriately
        7. Return the query with a brief explanation

        Examples:
        - "Show my recent orders" → SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC LIMIT 10
        - "What products are in Electronics category?" → SELECT * FROM products WHERE category = 'Electronics' LIMIT 20

        Return your response in JSON format:
        {{
            "query": "SQL_QUERY_HERE",
            "parameters": [param1, param2, ...],
            "explanation": "Brief explanation of what the query does"
        }}

        If no parameters are needed, use empty array: "parameters": []
        """)

        chain = prompt | self.llm | StrOutputParser()

        try:
            response = chain.invoke({
                "schema": schema,
                "query": user_query,
                "user_id": user_id
            })

            # Parse JSON response
            result = json.loads(response.strip())

            return SQLQuery(
                query=result["query"],
                parameters=result.get("parameters", []),
                explanation=result.get("explanation", "")
            )

        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            # Fallback to simple query
            return self._generate_fallback_query(user_query, user_id)

    def _generate_fallback_query(self, user_query: str, user_id: int) -> SQLQuery:
        """Generate fallback SQL query"""
        user_query_lower = user_query.lower()

        if "order" in user_query_lower:
            return SQLQuery(
                query="SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC LIMIT 10",
                parameters=[user_id],
                explanation="Get recent orders for the user"
            )
        elif "product" in user_query_lower:
            return SQLQuery(
                query="SELECT name, category, price, stock_quantity FROM products LIMIT 20",
                parameters=[],
                explanation="Get sample products"
            )
        elif "spent" in user_query_lower or "total" in user_query_lower:
            return SQLQuery(
                query="SELECT SUM(total_amount) as total_spent FROM orders WHERE user_id = ?",
                parameters=[user_id],
                explanation="Calculate total spending"
            )
        else:
            return SQLQuery(
                query="SELECT 'Please be more specific' as message",
                parameters=[],
                explanation="Generic fallback query"
            )

    def create_query_plan(self, complex_query: str) -> QueryPlan:
        """Create a multi-stage query plan for complex queries"""

        prompt = PromptTemplate.from_template("""
        Create a query plan for this complex database query: {query}

        The database has these tables: users, products, orders, order_items, payments

        Create a step-by-step plan:
        1. First, understand what information is needed
        2. Determine which tables need to be queried
        3. Identify any joins needed between tables
        4. Specify any filters or conditions
        5. Determine sorting and grouping
        6. Generate the final SQL query

        Return your response in JSON format:
        {{
            "steps": ["step1", "step2", "step3", ...],
            "final_query": "SELECT ...",
            "intermediate_queries": ["query1", "query2", ...]
        }}
        """)

        chain = prompt | self.llm | StrOutputParser()

        try:
            response = chain.invoke({"query": complex_query})
            result = json.loads(response.strip())

            # Execute intermediate queries to get sample results
            intermediate_results = []
            for query in result.get("intermediate_queries", []):
                try:
                    if query.strip().upper().startswith("SELECT"):
                        results = self.db_manager.execute_query(query)
                        intermediate_results.append({
                            "query": query,
                            "results_count": len(results),
                            "sample": results[:2] if results else []
                        })
                except:
                    pass

            return QueryPlan(
                steps=result["steps"],
                final_query=result["final_query"],
                intermediate_results=intermediate_results
            )

        except Exception as e:
            logger.error(f"Error creating query plan: {str(e)}")

            # Simple fallback plan
            return QueryPlan(
                steps=[
                    "1. Parse the user query",
                    "2. Generate appropriate SQL",
                    "3. Execute the query",
                    "4. Return results"
                ],
                final_query="SELECT * FROM users LIMIT 1",
                intermediate_results=[]
            )

    def generate_natural_response(self, data: List[Dict], original_query: str, sql_query: str) -> str:
        """Generate natural language response from query results"""

        if not data:
            return "I found no results matching your query."

        # Limit data for context
        data_sample = data[:10]
        data_str = json.dumps(data_sample, indent=2, default=str)

        prompt = PromptTemplate.from_template("""
        Original user query: {query}

        SQL Query used: {sql_query}

        Query Results (first {count} of {total} rows):
        {data}

        Generate a helpful, natural language response that:
        1. Directly answers the user's question
        2. Summarizes the key findings from the data
        3. Is concise but informative
        4. Mentions specific numbers or details when relevant
        5. If there are many results, mention that and summarize patterns

        Response:
        """)

        chain = prompt | self.llm | StrOutputParser()

        try:
            response = chain.invoke({
                "query": original_query,
                "sql_query": sql_query,
                "data": data_str,
                "count": len(data_sample),
                "total": len(data)
            })

            return response.strip()

        except Exception as e:
            logger.error(f"Error generating natural response: {str(e)}")
            return self._generate_fallback_response(data, original_query)

    def _generate_fallback_response(self, data: List[Dict], original_query: str) -> str:
        """Generate fallback natural language response"""
        if not data:
            return "No results found for your query."

        count = len(data)

        if count == 1:
            return f"Found 1 result matching your query."
        else:
            # Try to extract summary information
            summary_parts = [f"Found {count} results"]

            # Check for common numeric fields
            numeric_fields = ['total_amount', 'price', 'amount', 'quantity']
            for field in numeric_fields:
                if field in data[0]:
                    try:
                        total = sum(float(row.get(field, 0)) for row in data)
                        summary_parts.append(f"total {field}: {total:,.2f}")
                        break
                    except:
                        pass

            return f"{', '.join(summary_parts)}."

    def analyze_data(self, data: List[Dict], analysis_request: str) -> str:
        """Analyze data and provide insights"""

        if not data:
            return "No data to analyze."

        data_str = json.dumps(data[:20], indent=2, default=str)  # Limit for context

        prompt = PromptTemplate.from_template("""
        Data Analysis Request: {request}

        Data to analyze:
        {data}

        Please analyze this data and provide insights including:
        1. Key statistics (counts, sums, averages where applicable)
        2. Patterns or trends you observe
        3. Notable findings
        4. Recommendations or suggestions based on the data

        Analysis:
        """)

        chain = prompt | self.llm | StrOutputParser()

        try:
            response = chain.invoke({
                "request": analysis_request,
                "data": data_str
            })

            return response.strip()
        except Exception as e:
            logger.error(f"Error analyzing data: {str(e)}")
            return "Unable to analyze the data at this time."

    def analyze_query_results(self, results_description: str) -> str:
        """Analyze query results description"""

        prompt = PromptTemplate.from_template("""
        Analyze these query results and provide insights:

        {results}

        Provide a brief analysis of what these results mean.
        """)

        chain = prompt | self.llm | StrOutputParser()

        try:
            response = chain.invoke({"results": results_description})
            return response.strip()
        except:
            return "Analysis not available."