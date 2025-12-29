import logging
from typing import Dict, Any, Optional

from langchain.agents import create_agent
from langchain_classic.agents import AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import GoogleGenerativeAI
try:
    import google.generativeai as genai
    _HAS_GEMINI = True
except ImportError:
    genai = None
    _HAS_GEMINI = False

from app.llm_services import GeminiLLMService
from app.database import DatabaseManager
from app.tools import SchemaLookupTool
from app.tools import QueryExecutorTool
from app.tools import SampleDataTool
from app.tools import SQLGeneratorTool
from app.tools import DataAnalysisTool
from app.tools import MultiStageQueryPlanner


logger = logging.getLogger(__name__)


class GeminiSQLAgent:
    """SQL Agent powered by Google Gemini with the same functionality as SQLAgent"""

    def __init__(self, db_manager: DatabaseManager, llm_service: GeminiLLMService):
        if not _HAS_GEMINI:
            raise ValueError(
                "google-generativeai package not installed. "
                "Install it with: pip install google-generativeai"
            )

        self.db_manager = db_manager
        self.llm_service = llm_service
        self.tools = self._create_tools()
        self.agent_executor = self._create_agent()
        self.llm = GoogleGenerativeAI(model=self.llm_service.model)

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
        """Create the Gemini-powered agent with tools"""

        print("Creating Gemini Agent...")

        # System prompt
        system_prompt = """You are an intelligent SQL assistant powered by Google Gemini with access to an e-commerce database.

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
        6. Return only the final answer as a concise response. No explanations of your thought process.

        Always be helpful and provide clear explanations.
        Only use SELECT queries for security.
        For user-specific data, remember to filter by user_id.

        If you're unsure, ask for clarification or use the schema_lookup tool first.
        """

        # Create agent prompt
        react_prompt = PromptTemplate.from_template("""
        {system_prompt}

        Current conversation:
        {chat_history}

        User Query: {input}

        {agent_scratchpad}
        """)

        # Use Gemini as the LLM
        llm = genai.GenerativeModel(self.llm_service.model)

        # Create agent - Note: This uses the Gemini model directly
        # Since langchain's create_agent may not directly support Gemini,
        # we'll create a custom agent wrapper
        try:
            agent = create_agent(
                model=llm,
                tools=self.tools,
                system_prompt=system_prompt
            )
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=5,
                early_stopping_method="generate"
            )
        except Exception as e:
            logger.warning(f"Could not create agent with langchain integration: {e}")
            logger.info("Falling back to direct Gemini agent implementation")
            agent_executor = self._create_direct_gemini_agent()

        return agent_executor

    def _create_direct_gemini_agent(self) -> 'GeminiDirectAgent':
        """Create a direct Gemini agent without langchain agent framework"""
        return GeminiDirectAgent(self.db_manager, self.llm_service, self.tools)

    def process_query(self, user_query: str, user_id: int = 1) -> Dict[str, Any]:
        """Process user query using the Gemini agent"""
        try:
            context_query = f"User ID: {user_id}\nQuery: {user_query}"
            print("Context Query:", context_query)

            response = self.agent_executor.invoke({
                "input": context_query,
                "system_prompt": f"Current User ID: {user_id}"
            })

            sql_queries = self._extract_sql_queries(response)

            data = []
            if sql_queries:
                last_query = sql_queries[-1]
                if last_query.upper().startswith("SELECT"):
                    try:
                        data = self.db_manager.execute_query(last_query)
                    except Exception as e:
                        logger.error(f"Error executing extracted query: {str(e)}")

            return {
                "response": response["output"] if isinstance(response, dict) else str(response),
                "sql_queries": sql_queries,
                "data": data[:10] if data else None,
                "error": None
            }

        except Exception as e:
            logger.error(f"Gemini Agent error: {str(e)}")
            return {
                "response": f"I encountered an error: {str(e)}",
                "sql_queries": [],
                "data": None,
                "error": str(e)
            }

    def _extract_sql_queries(self, agent_response: Any) -> list:
        """Extract SQL queries from agent response"""
        import re

        queries = []
        
        # Handle different response types
        if isinstance(agent_response, dict):
            output = agent_response.get("output", "")
        else:
            output = str(agent_response)

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


class GeminiDirectAgent:
    """Direct Gemini agent implementation without langchain agent framework"""

    def __init__(self, db_manager: DatabaseManager, llm_service: GeminiLLMService, tools: list):
        self.db_manager = db_manager
        self.llm_service = llm_service
        self.tools = {tool.name: tool for tool in tools}

    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the direct Gemini agent"""
        user_query = inputs.get("input", "")
        system_prompt = inputs.get("system_prompt", "")

        # Build prompt with tool descriptions
        tool_descriptions = "\n".join([
            f"- {name}: {tool.description if hasattr(tool, 'description') else 'Tool'}"
            for name, tool in self.tools.items()
        ])

        full_prompt = f"""You are an intelligent SQL assistant powered by Google Gemini.

System: {system_prompt}

Available Tools:
{tool_descriptions}

User Query: {user_query}

Respond with:
1. Your analysis
2. Any SQL queries you generate
3. The final answer

"""
        try:
            model = genai.GenerativeModel(self.llm_service.model)
            response = model.generate_content(full_prompt)
            output = response.text if response else "No response"

            return {
                "output": output,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Direct Gemini agent error: {e}")
            return {
                "output": f"Error: {str(e)}",
                "status": "error"
            }


class GeminiDirectSQLGenerator:
    """Direct SQL generation using Gemini - Alternative to agent"""

    def __init__(self, db_manager: DatabaseManager, llm_service: GeminiLLMService):
        self.db_manager = db_manager
        self.llm_service = llm_service

    def process_query(self, user_query: str, user_id: int = 1) -> Dict[str, Any]:
        """Process query directly without agent"""
        try:
            # Generate SQL using Gemini
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
            logger.error(f"Direct SQL generation error with Gemini: {str(e)}")
            return {
                "response": f"Error: {str(e)}",
                "sql_query": None,
                "data": None,
                "error": str(e)
            }


def create_agent(agent_type: str = "openai", db_manager: Optional[DatabaseManager] = None, 
                 llm_service: Optional[Any] = None) -> Any:
    """Factory function to create either OpenAI or Gemini agent"""
    if db_manager is None or llm_service is None:
        raise ValueError("db_manager and llm_service are required")

    agent_type = (agent_type or "openai").lower().strip()

    if agent_type == "gemini":
        if not isinstance(llm_service, GeminiLLMService):
            raise ValueError("For Gemini agent, llm_service must be a GeminiLLMService instance")
        return GeminiSQLAgent(db_manager, llm_service)
    elif agent_type == "openai":
        from app.agents import SQLAgent
        return SQLAgent(db_manager, llm_service)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}. Use 'openai' or 'gemini'.")


def create_direct_sql_generator(generator_type: str = "openai", db_manager: Optional[DatabaseManager] = None,
                                llm_service: Optional[Any] = None) -> Any:
    """Factory function to create either OpenAI or Gemini direct SQL generator"""
    if db_manager is None or llm_service is None:
        raise ValueError("db_manager and llm_service are required")

    generator_type = (generator_type or "openai").lower().strip()

    if generator_type == "gemini":
        if not isinstance(llm_service, GeminiLLMService):
            raise ValueError("For Gemini SQL generator, llm_service must be a GeminiLLMService instance")
        return GeminiDirectSQLGenerator(db_manager, llm_service)
    elif generator_type == "openai":
        from app.agents import DirectSQLGenerator
        return DirectSQLGenerator(db_manager, llm_service)
    else:
        raise ValueError(f"Unknown generator type: {generator_type}. Use 'openai' or 'gemini'.")
