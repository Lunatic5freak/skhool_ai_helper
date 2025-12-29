import logging
import json
from typing import Dict, Any, Optional
# from langchain.agents.agent import AgentExecutor
# from langchain.agents.react.agent import create_react_agent

from langchain.agents import  create_agent
from langchain_classic.agents import AgentExecutor
# from langchain_core.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from app.llm_services import LLMService
from app.database import DatabaseManager
from app.tools import SchemaLookupTool
from app.tools import QueryExecutorTool
from app.tools import SampleDataTool
from app.tools import SQLGeneratorTool
from app.tools import DataAnalysisTool
from app.tools import MultiStageQueryPlanner
from app.agents_google import GeminiSQLAgent


logger = logging.getLogger(__name__)


class SQLAgent:
    def __init__(self, type: str, db_manager: DatabaseManager, llm_service: LLMService):
        self.type = type
        self.db_manager = db_manager
        self.llm_service = llm_service
        self.tools = self._create_tools()
        self.agent = self.type == 'gemini' and GeminiSQLAgent(db_manager, llm_service) or self._create_agent()
        # self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    def _create_tools(self) -> list:
        """Create all tools for the agent"""

        tools = [
            SchemaLookupTool(db_manager=self.db_manager),
            QueryExecutorTool(db_manager=self.db_manager),
            SampleDataTool(db_manager=self.db_manager),
            SQLGeneratorTool(llm_service=self.llm_service),
            DataAnalysisTool(llm_service=self.llm_service),
            MultiStageQueryPlanner(db_manager=self.db_manager, llm_service=self.llm_service)
        ]

        return tools

    def _create_agent(self) -> AgentExecutor:
        """Create the ReAct agent with tools"""

        print("Creating openai Agent...")

        # System prompt
        system_prompt = """You are an intelligent SQL assistant with access to an e-commerce database.

        You have access to the following tools:
        1. schema_lookup: Look up database schema information
        2. query_executor: Execute SQL SELECT queries
        3. sample_data: Get sample data from tables
        4. sql_generator: Generate SQL queries from natural language
        5. data_analyzer: Analyze query results
        6. query_planner: Plan and execute complex multi-stage queries

        Workflow for complex queries:
        1. Use schema_lookup to understand the database structure if needed
        2. Use sample_data to see example data if needed
        3. Use sql_generator or query_planner for complex queries
        4. Use query_executor to run the query
        5. Use data_analyzer to provide insights on results

        Always be helpful and provide clear explanations.
        Only use SELECT queries for security.
        For user-specific data, remember to filter by user_id.

        If you're unsure, ask for clarification or use the schema_lookup tool first.
        """

        # Create React agent prompt
        react_prompt = PromptTemplate.from_template("""
        {system_prompt}

        Current conversation:
        {chat_history}

        User Query: {input}

        {agent_scratchpad}
        """)


        llm = ChatOpenAI(
            model=self.llm_service.model,
            temperature=0.1,
            api_key=self.llm_service.api_key
        )

        # Create agent
        agent = create_agent(
            model=llm,
            tools=self.tools,
            system_prompt=system_prompt
        )

        # Create executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            # memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            early_stopping_method="generate"
        )

        return agent_executor

    def process_query(self, user_query: str, user_id: int = 1) -> Dict[str, Any]:
        """Process user query using the agent"""

        try:
            # Add user context to the query
            context_query = f"User ID: {user_id}\nQuery: {user_query}"
            print(self.type)
            print("Context Query:", context_query)
            # Invoke the agent
            response = self.agent.agent_executor.invoke({
                "input": context_query,
                "system_prompt": f"Current User ID: {user_id}. Only access data for this user. Use the tools as needed and return only the final answer. Use DataAnalysisTool to analyze data after executing SQL queries and return the result in string format"
            })

            print("Agent Response:", response)
            pretty_response = self.agent.llm.invoke([
                "Convert SQL result into a clear Markdown answer for user query.",
                f"User query: {user_query}",
                f"Results: {json.dumps(response, indent=2)}"
            ])
            print("Pretty Response:", pretty_response)
            return pretty_response

            # # Extract SQL queries from the agent's actions
            # sql_queries = self._extract_sql_queries(response)

            # # Execute the last SQL query to get data
            # data = []
            # if sql_queries:
            #     last_query = sql_queries[-1]
            #     if last_query.upper().startswith("SELECT"):
            #         try:
            #             data = self.db_manager.execute_query(last_query)
            #         except Exception as e:
            #             logger.error(f"Error executing extracted query: {str(e)}")

            return {
                "response": response
            }

        except Exception as e:
            logger.error(f"Agent error: {str(e)}")
            return {
                "response": f"I encountered an error: {str(e)}",
                "sql_queries": [],
                "data": None,
                "error": str(e)
            }

    def _extract_sql_queries(self, agent_response: Dict[str, Any]) -> list:
        """Extract SQL queries from agent response"""
        import re

        queries = []
        output = agent_response.get("output", "")

        # Look for SQL blocks
        sql_patterns = [
            r"```sql\n(.*?)\n```",
            r"```\n(.*?)\n```",
            r"SELECT.*?(?=\n\n|$)",
            r"select.*?(?=\n\n|$)"
        ]

        for pattern in sql_patterns:
            matches = re.findall(pattern, output, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if match.strip() and match.strip().upper().startswith("SELECT"):
                    queries.append(match.strip())

        return list(set(queries))  # Remove duplicates


class DirectSQLGenerator:
    """Alternative: Direct SQL generation without agent"""

    def __init__(self, db_manager: DatabaseManager, llm_service: LLMService):
        self.db_manager = db_manager
        self.llm_service = llm_service

    def process_query(self, user_query: str, user_id: int = 1) -> Dict[str, Any]:
        """Process query directly without agent"""

        try:
            # Generate SQL
            sql_obj = self.llm_service.generate_sql_from_natural_language(user_query, user_id)

            # Execute query
            if sql_obj.parameters:
                data = self.db_manager.execute_query(sql_obj.query, tuple(sql_obj.parameters))
            else:
                data = self.db_manager.execute_query(sql_obj.query)

            # Generate natural response
            natural_response = self.llm_service.generate_natural_response(
                data, user_query, sql_obj.query
            )

            return {
                "response": natural_response,
                "sql_query": sql_obj.query,
                "data": data[:10] if data else None,
                "error": None
            }

        except Exception as e:
            logger.error(f"Direct SQL generation error: {str(e)}")
            return {
                "response": f"Error: {str(e)}",
                "sql_query": None,
                "data": None,
                "error": str(e)
            }