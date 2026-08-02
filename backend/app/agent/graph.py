"""LangGraph-based text-to-SQL agent with tool calling and self-improvement."""

import logging
import json
from typing import Annotated, TypedDict, Literal, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.tools import tool

from app.config import settings
from app.agent.prompts import SYSTEM_PROMPT, USER_QUERY_PROMPT
from app.agent.tools import tool_registry
from app.services.training_service import get_training_context, build_training_prompt

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    question: str
    db_connection_id: int
    training_context: str
    similar_examples: str
    sql: Optional[str]
    query_result: Optional[str]
    chart_data: Optional[list]  # list of ECharts option JSON strings
    final_response: Optional[str]
    success: bool
    tool_names_used: list[str]
    tool_params_used: list[dict]


def create_tools():
    """Create LangChain tools bound to the tool registry."""

    @tool
    async def execute_sql(sql: str) -> str:
        """Execute a SQL query on the target database. Input: SQL string. Output: JSON with columns and rows."""
        return await tool_registry.execute_sql(sql)

    @tool
    async def get_schema(table_name: Optional[str] = None) -> str:
        """Get database schema. Optional table_name to filter. Output: JSON with table schemas."""
        return await tool_registry.get_schema(table_name)

    @tool
    async def get_table_sample(table_name: str, limit: int = 5) -> str:
        """Get sample data from a table. Input: table_name. Output: JSON with columns and sample rows."""
        return await tool_registry.get_table_sample(table_name, limit)

    @tool
    def generate_chart(title: str, echarts_option: str) -> str:
        """生成 ECharts 图表。echarts_option 是完整的 Apache ECharts 配置 JSON，
        包含 title、tooltip、xAxis、yAxis、series 等字段。可生成柱状图、折线图、饼图、散点图、热力图等。"""
        return tool_registry.generate_chart(title, echarts_option)

    @tool
    async def get_similar_examples(question: str) -> str:
        """Find similar past successful tool usage examples. Input: question text."""
        return await tool_registry.get_similar_examples(question)

    return [execute_sql, get_schema, get_table_sample, generate_chart, get_similar_examples]


def _create_llm():
    """Create LLM instance based on configured provider."""
    if settings.LLM_PROVIDER == "deepseek":
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
    else:
        return ChatOpenAI(
            model=settings.LLM_MODEL or settings.OPENAI_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            api_key=settings.effective_api_key,
            base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None,
        )


def build_agent_graph():
    """Build the LangGraph agent workflow for text-to-SQL."""

    llm = _create_llm()

    tools_list = create_tools()
    # Build name → function mapping for manual tool invocation
    tool_map = {t.name: t for t in tools_list}
    llm_with_tools = llm.bind_tools(tools_list)

    async def initialize(state: AgentState) -> AgentState:
        question = state["question"]
        training_ctx = state.get("training_context", "")
        similar = state.get("similar_examples", "")

        user_content = USER_QUERY_PROMPT.format(
            question=question,
            training_context=training_ctx if training_ctx else "（暂无训练数据）",
            similar_examples=similar if similar else "（暂无历史相似案例）",
        )

        state["messages"] = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]
        state["tool_names_used"] = []
        state["tool_params_used"] = []
        state["success"] = True
        return state

    async def call_model(state: AgentState) -> AgentState:
        messages = state["messages"]
        response = await llm_with_tools.ainvoke(messages)
        state["messages"] = [response]
        return state

    def should_continue(state: AgentState) -> Literal["tools", "finalize"]:
        last_msg = state["messages"][-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            for tc in last_msg.tool_calls:
                state["tool_names_used"].append(tc["name"])
                state["tool_params_used"].append(tc.get("args", {}))
            return "tools"
        return "finalize"

    async def process_tools(state: AgentState) -> AgentState:
        """Manually invoke tools and return ToolMessages."""
        last_msg = state["messages"][-1]
        tool_messages = []

        for tc in last_msg.tool_calls:
            tool_name = tc["name"]
            tool_args = tc.get("args", {})
            tool_id = tc.get("id", "")

            logger.info(f"Invoking tool: {tool_name} with args: {json.dumps(tool_args, ensure_ascii=False)[:300]}")

            if tool_name in tool_map:
                try:
                    tool_func = tool_map[tool_name]
                    # tool_func 是 @tool 装饰的 StructuredTool，ainvoke 在 BaseTool 基类定义
                    result = await tool_func.ainvoke(tool_args)
                    original_result = str(result)
                    logger.info(f"Tool {tool_name} succeeded, result length: {len(original_result)}")

                    # Save SQL and chart data to state before truncating
                    if tool_name == "execute_sql":
                        state["query_result"] = original_result
                    elif tool_name == "generate_chart":
                        charts = state.get("chart_data", []) or []
                        charts.append(original_result)
                        state["chart_data"] = charts

                    # Truncate large results for LLM context (state keeps full data)
                    llm_result = original_result
                    if tool_name == "generate_chart" and len(llm_result) > 2000:
                        try:
                            parsed = json.loads(llm_result)
                            if "echarts_option" in parsed:
                                opt = parsed["echarts_option"]
                                parsed["echarts_option"] = {"_summary": f"[{opt.get('title',{}).get('text','')} {len(json.dumps(opt))} bytes]"}
                            parsed["hint"] = f"[图表配置已生成]"
                            llm_result = json.dumps(parsed, ensure_ascii=False)
                        except (json.JSONDecodeError, TypeError):
                            llm_result = '{"message": "图表已生成"}'
                    elif tool_name == "execute_sql" and len(llm_result) > 4000:
                        try:
                            parsed = json.loads(llm_result)
                            row_count = parsed.get("row_count", 0)
                            parsed["rows"] = parsed.get("rows", [])[:50]
                            parsed["hint"] = f"[显示前50行，共 {row_count} 行]"
                            llm_result = json.dumps(parsed, ensure_ascii=False)
                        except (json.JSONDecodeError, TypeError):
                            llm_result = llm_result[:2000] + "..."
                    elif len(llm_result) > 4000:
                        llm_result = llm_result[:2000] + f"\n...[截断，共 {len(llm_result)} 字节]"
                except Exception as e:
                    logger.exception(f"Tool {tool_name} failed: {e}")
                    llm_result = json.dumps({"error": str(e)})
            else:
                logger.warning(f"Unknown tool requested: {tool_name}")
                llm_result = json.dumps({"error": f"Unknown tool: {tool_name}"})

            tool_messages.append(ToolMessage(content=llm_result, tool_call_id=tool_id, name=tool_name))

        state["messages"] = tool_messages
        return state

    async def finalize(state: AgentState) -> AgentState:
        messages = state["messages"]
        final_text = ""

        # Collect SQL text
        sql_text = None
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] == "execute_sql":
                        sql_text = tc["args"].get("sql")

        # Collect final response text
        for msg in messages:
            if isinstance(msg, AIMessage) and msg.content:
                final_text += str(msg.content)

        state["final_response"] = final_text
        state["sql"] = sql_text
        # chart_data and query_result already saved in process_tools

        if sql_text or state.get("chart_data") or state.get("query_result"):
            summary = ""
            if sql_text:
                summary += f"```sql\n{sql_text}\n```\n\n"
            if final_text:
                summary += final_text
            state["messages"].append(AIMessage(content=summary or "分析完成"))

        return state

    workflow = StateGraph(AgentState)

    workflow.add_node("initialize", initialize)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", process_tools)
    workflow.add_node("finalize", finalize)

    workflow.set_entry_point("initialize")
    workflow.add_edge("initialize", "agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "finalize": "finalize"})
    workflow.add_edge("tools", "agent")
    workflow.add_edge("finalize", END)

    return workflow.compile()


agent_graph = build_agent_graph()


async def run_analysis(
    question: str,
    db_connection_id: int,
    training_context: str,
    similar_examples: str,
) -> dict:
    initial_state: AgentState = {
        "messages": [],
        "question": question,
        "db_connection_id": db_connection_id,
        "training_context": training_context,
        "similar_examples": similar_examples,
        "sql": None,
        "query_result": None,
        "chart_data": None,
        "final_response": None,
        "success": True,
        "tool_names_used": [],
        "tool_params_used": [],
    }

    try:
        final_state = await agent_graph.ainvoke(initial_state)
        return {
            "question": question,
            "sql": final_state.get("sql"),
            "result": final_state.get("query_result"),
            "explanation": final_state.get("final_response"),
            "chart_data": final_state.get("chart_data"),
            "success": final_state.get("success", True),
            "tool_names_used": final_state.get("tool_names_used", []),
            "tool_params_used": final_state.get("tool_params_used", []),
        }
    except Exception as e:
        error_str = str(e)
        logger.exception(f"Agent execution failed: {error_str}")

        # Friendly messages for known errors
        if "503" in error_str or "service_unavailable" in error_str.lower() or "too busy" in error_str.lower():
            user_msg = "DeepSeek 服务当前繁忙，请稍后重试。建议等待 30 秒后再次提交问题。"
        elif "401" in error_str or "authentication" in error_str.lower():
            user_msg = "API Key 无效，请检查 DeepSeek 密钥配置。"
        elif "429" in error_str or "rate" in error_str.lower():
            user_msg = "API 调用频率过高，请稍后重试。"
        elif "timeout" in error_str.lower() or "timed out" in error_str.lower():
            user_msg = "请求超时，DeepSeek 服务响应过慢，请重试。"
        else:
            user_msg = f"分析过程中出错: {error_str}"

        return {
            "question": question,
            "sql": None,
            "result": None,
            "explanation": user_msg,
            "chart_data": None,
            "success": False,
            "tool_names_used": [],
            "tool_params_used": [],
            "error": error_str,
        }
