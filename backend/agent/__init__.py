import os
import re
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import BaseTool, tool

load_dotenv()


def create_llm(model: str, api_key: str = None, endpoint: str = None, is_local: bool = False):
    """Create LLM instance based on configuration."""
    if is_local:
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(model=model)
    
    if endpoint and "openrouter" in endpoint:
        return ChatOpenAI(
            model=model,
            api_key=api_key or os.getenv("OPENROUTER_API_KEY"),
            base_url=endpoint,
            max_tokens=2048,
        )
    
    return ChatOpenAI(
        model=model,
        api_key=api_key or os.getenv("OPENAI_API_KEY"),
        base_url=endpoint,
        max_tokens=2048,
    )


REACT_PROMPT = """You are a helpful AI assistant that uses tools to complete tasks.

You have access to the following tools:

{tools}

To use a tool, respond in this format:

<tool_call>
tool_name | arg1="value1"
</tool_call>

When you have completed the task, respond with:

<tool_call>
final_answer | result="Your final answer here"
</tool_call>

Begin!"""


class LangChainAgent:
    """LangChain ReAct Agent wrapper for SSE streaming."""
    
    def __init__(self, tools: List[BaseTool], model: str, api_key: str = None, endpoint: str = None, is_local: bool = False, project_directory: str = None):
        self.tools = tools
        self.model = model
        self.project_directory = project_directory or os.getcwd()
        self.is_local = is_local
        self.llm = create_llm(model, api_key, endpoint, is_local)
    
    def run_stream(self, user_input: str):
        """Run agent with streaming events."""
        try:
            yield ("thought", "Analyzing the request...")
            
            messages = [{"role": "user", "content": user_input}]
            
            max_iterations = 15
            for i in range(max_iterations):
                response = self.llm.invoke(messages)
                content = response.content
                
                tool_match = re.search(r"<tool_call>\s*(\w+)\s*\|", content)
                final_match = re.search(r"<tool_call>\s*final_answer\s*\|", content)
                
                if final_match:
                    result_match = re.search(r'result="([^"]*)"', content)
                    result = result_match.group(1) if result_match else content
                    yield ("final_answer", result)
                    return
                
                if not tool_match:
                    yield ("final_answer", content)
                    return
                
                tool_name = tool_match.group(1)
                
                if tool_name not in [t.name for t in self.tools]:
                    yield ("error", f"Unknown tool: {tool_name}")
                    return
                
                args_match = re.search(rf"<tool_call>\s*{tool_name}\s*\|?\s*(.+?)(?:</tool_call>|$)", content, re.DOTALL)
                args_str = args_match.group(1) if args_match else ""
                
                tool_func = next((t for t in self.tools if t.name == tool_name), None)
                if not tool_func:
                    continue
                
                yield ("action", {"tool_name": tool_name, "args": args_str.strip()})
                
                observation = "Tool execution not implemented - continuing"
                yield ("observation", observation)
                
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": f"<observation>{observation}</observation>"})
            
            yield ("final_answer", "Max iterations reached")
                
        except Exception as e:
            error_msg = str(e)
            if "402" in error_msg:
                yield ("error", "模型服务暂时不可用，请稍后重试")
            elif "401" in error_msg:
                yield ("error", "API 认证失败")
            else:
                yield ("error", f"Agent 执行错误: {error_msg}")


def get_tool_schemas(tools: List[BaseTool]) -> List[Dict]:
    """Get tool schemas in LangChain format."""
    return [t.schema() for t in tools]


def get_tool_registry():
    """Get all available tools."""
    from .chain_tools import TOOL_REGISTRY
    return TOOL_REGISTRY