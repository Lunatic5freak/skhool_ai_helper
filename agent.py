"""
LangGraph-based School Management Chatbot Agent.
Multi-step reasoning with database query capabilities and RBAC.
"""
from typing import TypedDict, Annotated, Sequence, Optional, Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import Tool, StructuredTool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, FunctionMessage
from pydantic import BaseModel, Field
import operator
import logging
import json

from config import get_settings
from auth import AuthPayload, RBACService
from db_tools import DatabaseQueryTools
from models import UserRole

logger = logging.getLogger(__name__)


# Agent State
class AgentState(TypedDict):
    """State for the school chatbot agent."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_query: str
    schema_name: str
    auth_payload: Dict[str, Any]
    intermediate_steps: Annotated[List[tuple], operator.add]
    final_answer: Optional[str]
    error: Optional[str]


# Tool Input Schemas
class StudentInfoInput(BaseModel):
    """Input for getting student information."""
    student_id: Optional[str] = Field(
        None, 
        description="Student ID. Leave empty to get current user's info if they are a student."
    )


class AttendanceInput(BaseModel):
    """Input for getting attendance data."""
    student_id: Optional[str] = Field(
        None,
        description="Student ID. Leave empty for current student user."
    )
    start_date: Optional[str] = Field(
        None,
        description="Start date in YYYY-MM-DD format"
    )
    end_date: Optional[str] = Field(
        None,
        description="End date in YYYY-MM-DD format"
    )


class ExamResultsInput(BaseModel):
    """Input for getting exam results."""
    student_id: Optional[str] = Field(
        None,
        description="Student ID. Leave empty for current student user."
    )
    subject_name: Optional[str] = Field(
        None,
        description="Filter by subject name"
    )
    exam_type: Optional[str] = Field(
        None,
        description="Filter by exam type: midterm, final, quiz, assignment, project"
    )


class PerformanceAnalysisInput(BaseModel):
    """Input for performance analysis."""
    student_id: Optional[str] = Field(
        None,
        description="Student ID. Leave empty for current student user."
    )


class ClassPerformanceInput(BaseModel):
    """Input for class performance (Admin/Teacher only)."""
    class_id: str = Field(..., description="Class ID to analyze")


class SchoolChatbotAgent:
    """LangGraph-based school chatbot agent with RBAC."""
    
    def __init__(
        self,
        schema_name: str,
        auth_payload: AuthPayload
    ):
        """
        Initialize the chatbot agent.
        
        Args:
            schema_name: Tenant schema name
            auth_payload: Authentication payload for RBAC
        """
        self.settings = get_settings()
        self.schema_name = schema_name
        self.auth_payload = auth_payload
        self.db_tools = DatabaseQueryTools(schema_name, auth_payload)
        
        # Initialize LLM based on provider
        self.llm = self._initialize_llm()
        
        # Create tools
        self.tools = self._create_tools()
        self.tool_executor = ToolExecutor(self.tools)
        
        # Create LangGraph workflow
        self.workflow = self._create_workflow()
        self.app = self.workflow.compile()
    
    def _initialize_llm(self):
        """Initialize LLM based on configured provider."""
        provider = self.settings.llm_provider.lower()
        
        if provider == "anthropic":
            if not self.settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic provider")
            return ChatAnthropic(
                model=self.settings.default_model,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
                anthropic_api_key=self.settings.anthropic_api_key,
            )
        
        elif provider == "openai":
            if not self.settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
            return ChatOpenAI(
                model=self.settings.default_model,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
                openai_api_key=self.settings.openai_api_key,
            )
        
        elif provider == "google":
            if not self.settings.google_api_key:
                raise ValueError("GOOGLE_API_KEY is required when using Google provider")
            return ChatGoogleGenerativeAI(
                model=self.settings.default_model,
                temperature=self.settings.temperature,
                max_output_tokens=self.settings.max_tokens,
                google_api_key=self.settings.google_api_key,
            )
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent."""
        tools = [
            StructuredTool.from_function(
                func=self.db_tools.get_student_info,
                name="get_student_info",
                description=(
                    "Get detailed information about a student including name, class, roll number, "
                    "contact details. Students can only access their own information."
                ),
                args_schema=StudentInfoInput
            ),
            StructuredTool.from_function(
                func=self.db_tools.get_student_attendance,
                name="get_attendance",
                description=(
                    "Get attendance report for a student including total days, present/absent days, "
                    "attendance percentage, and recent absences. Can filter by date range."
                ),
                args_schema=AttendanceInput
            ),
            StructuredTool.from_function(
                func=self.db_tools.get_exam_results,
                name="get_exam_results",
                description=(
                    "Get exam results for a student. Can filter by subject name or exam type "
                    "(midterm, final, quiz, assignment, project). Shows marks, percentage, and grades."
                ),
                args_schema=ExamResultsInput
            ),
            StructuredTool.from_function(
                func=self.db_tools.get_performance_analysis,
                name="get_performance_analysis",
                description=(
                    "Get comprehensive performance analysis including overall statistics, "
                    "subject-wise performance, grade distribution, insights, and personalized "
                    "recommendations for improvement."
                ),
                args_schema=PerformanceAnalysisInput
            ),
            StructuredTool.from_function(
                func=self.db_tools.get_class_performance,
                name="get_class_performance",
                description=(
                    "Get class-wide performance statistics. Only available for admin and teacher roles. "
                    "Shows average performance, total students, and exam statistics."
                ),
                args_schema=ClassPerformanceInput
            ),
        ]
        return tools
    
    def _get_system_prompt(self) -> str:
        """Get role-specific system prompt."""
        role = UserRole(self.auth_payload.role)
        user_name = self.auth_payload.email.split('@')[0]
        
        base_prompt = f"""You are an intelligent assistant for a school management system. 

Current User: {user_name}
Role: {role.value.title()}
"""
        
        if role == UserRole.STUDENT:
            base_prompt += f"""
Student ID: {self.auth_payload.student_id}

You are helping a student access their academic information. You can:
- Show their attendance records and patterns
- Display their exam results and grades
- Provide performance analysis and insights
- Suggest study recommendations based on their performance
- Answer questions about their academic progress

You can ONLY access this student's own data due to privacy policies.
"""
        elif role == UserRole.TEACHER:
            base_prompt += f"""
Teacher ID: {self.auth_payload.teacher_id}

You are helping a teacher manage their classes and students. You can:
- View student performance in their classes
- Access attendance records
- View exam results and class statistics
- Provide insights on student progress
- Generate class-wide reports

You can access data for students in your classes.
"""
        elif role == UserRole.ADMIN:
            base_prompt += """
You are helping a school administrator. You can:
- View all students, teachers, and classes
- Generate comprehensive reports
- Access attendance and performance data across the school
- Provide school-wide analytics and insights

You have full access to all school data.
"""
        
        base_prompt += """

When responding:
1. Be helpful, professional, and encouraging
2. Provide clear, actionable insights
3. Use the available tools to fetch accurate data
4. Format numerical data clearly (use tables when appropriate)
5. Offer constructive feedback and recommendations
6. Respect data privacy and RBAC rules
7. If a query requires data you don't have access to, politely explain the limitation

Available tools:
- get_student_info: Get student details
- get_attendance: Get attendance records
- get_exam_results: Get exam results
- get_performance_analysis: Get comprehensive performance analysis
- get_class_performance: Get class statistics (Admin/Teacher only)

Always use tools to fetch current data rather than making assumptions.
"""
        return base_prompt
    
    def _create_workflow(self) -> StateGraph:
        """Create LangGraph workflow."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", self.agent_node)
        workflow.add_node("tools", self.tool_node)
        workflow.add_node("generate_response", self.generate_response_node)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add edges
        workflow.add_conditional_edges(
            "agent",
            self.should_continue,
            {
                "continue": "tools",
                "end": "generate_response"
            }
        )
        workflow.add_edge("tools", "agent")
        workflow.add_edge("generate_response", END)
        
        return workflow
    
    async def agent_node(self, state: AgentState) -> AgentState:
        """Agent reasoning node."""
        messages = state["messages"]
        
        # Create prompt with system message
        system_message = SystemMessage(content=self._get_system_prompt())
        all_messages = [system_message] + list(messages)
        
        # Bind tools to LLM
        llm_with_tools = self.llm.bind_tools(self.tools)
        
        try:
            response = await llm_with_tools.ainvoke(all_messages)
            return {
                "messages": [response],
                "intermediate_steps": []
            }
        except Exception as e:
            logger.error(f"Agent node error: {e}")
            return {
                "messages": [],
                "error": str(e)
            }
    
    async def tool_node(self, state: AgentState) -> AgentState:
        """Execute tools."""
        messages = state["messages"]
        last_message = messages[-1]
        
        outputs = []
        
        # Execute tool calls
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                try:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                    
                    # Find and execute tool
                    tool = next((t for t in self.tools if t.name == tool_name), None)
                    if tool:
                        result = await tool.ainvoke(tool_args)
                        
                        # Create function message
                        function_message = FunctionMessage(
                            content=json.dumps(result),
                            name=tool_name,
                            tool_call_id=tool_call["id"]
                        )
                        outputs.append(function_message)
                        
                        # Log step
                        state["intermediate_steps"].append((tool_name, result))
                    else:
                        logger.error(f"Tool not found: {tool_name}")
                        
                except Exception as e:
                    logger.error(f"Tool execution error: {e}")
                    error_message = FunctionMessage(
                        content=json.dumps({"error": str(e)}),
                        name=tool_call.get("name", "unknown"),
                        tool_call_id=tool_call.get("id", "unknown")
                    )
                    outputs.append(error_message)
        
        return {"messages": outputs}
    
    async def generate_response_node(self, state: AgentState) -> AgentState:
        """Generate final response."""
        messages = state["messages"]
        last_message = messages[-1]
        
        # Extract content
        if hasattr(last_message, "content"):
            final_answer = last_message.content
        else:
            final_answer = str(last_message)
        
        return {"final_answer": final_answer}
    
    def should_continue(self, state: AgentState) -> str:
        """Determine if agent should continue or end."""
        messages = state["messages"]
        last_message = messages[-1]
        
        # If there are tool calls, continue to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        
        # Otherwise, generate final response
        return "end"
    
    async def chat(self, user_message: str) -> str:
        """
        Process user message and generate response.
        
        Args:
            user_message: User's query
            
        Returns:
            Agent's response
        """
        try:
            # Initialize state
            initial_state = {
                "messages": [HumanMessage(content=user_message)],
                "user_query": user_message,
                "schema_name": self.schema_name,
                "auth_payload": self.auth_payload.model_dump(),
                "intermediate_steps": [],
                "final_answer": None,
                "error": None
            }
            
            # Run workflow
            result = await self.app.ainvoke(initial_state)
            
            if result.get("error"):
                return f"I encountered an error: {result['error']}"
            
            return result.get("final_answer", "I couldn't generate a response.")
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return f"I'm sorry, I encountered an error: {str(e)}"


def create_chatbot_agent(
    schema_name: str,
    auth_payload: AuthPayload
) -> SchoolChatbotAgent:
    """
    Create and return a chatbot agent instance.
    
    Args:
        schema_name: Tenant schema name
        auth_payload: Authentication payload
        
    Returns:
        SchoolChatbotAgent instance
    """
    return SchoolChatbotAgent(schema_name, auth_payload)