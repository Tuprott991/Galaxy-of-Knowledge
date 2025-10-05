import asyncio
import json
import os
from typing import Any

from dotenv import load_dotenv
from google.adk.agents.llm_agent import LlmAgent
from google.adk.artifacts.in_memory_artifact_service import (
    InMemoryArtifactService,  # Optional
)
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
from google.genai import types
from google.auth import load_credentials_from_file
from rich import print

from google.adk.sessions import InMemorySessionService, Session
from google.adk.sessions import DatabaseSessionService # Store sessions in DB

db_url = os.getenv("DATABASE_URL")
if db_url is None:
    raise ValueError("DATABASE_URL environment variable is not set.")

# session_service = DatabaseSessionService(db_url=db_url)


load_dotenv()

from .config import config

def get_tools_async():
    """Gets tools from the MCP Server."""
    tools, exit_stack =  MCPToolset(
                connection_params=SseConnectionParams(
                    url='http://localhost:8081/sse',
                    headers={'Accept': 'text/event-stream'},
                ),
            )
    print("MCP Toolset created successfully.")
    return tools, exit_stack

def create_agent():
    
    # Get MCP tools
    # tools, exit_stack = asyncio.run(get_tools_async())
    # print(f"Retrieved {len(tools)} tools from MCP server.")

    agent = LlmAgent(
        model=config.model,
        name=config.agent_name,
        instruction="""You are an Intelligent Researcher Agent major in NASA Biology publication your name is SoftAI Bot.
Your goal is to assist users in finding relevant information from a collection of biology research papers published by NASA. You have access to the following tools:

You will be provided with a paper ID, which you can use to retrieve the full content of a specific research paper. Use this tool when you need detailed information from a particular paper.

Available tools:
1. get_document_content: Use this tool to get the full content of a specific research paper using its unique paper ID.

This tools can be use for multiple times in a single conversation for different paper IDs.
It's mean besides the first paper ID user provide, there also be other paper IDs including by the frontend because this system know the relation of the papers through the knowledge graph.

Only use the tools listed above. Do not make up any tools or APIs that do not exist.
There some cases that get_document_content tool use on different paper ID can be:
- Explore the similar papers to the first paper ID user provide.
- Find more details about a specific topic mentioned in the first paper ID.
- Compare findings across multiple papers.
Guidelines:
- Always think step-by-step before answering.
- Use the tools to gather information as needed.- Provide clear, concise, and accurate responses based on the information retrieved.
- Provide clear, concise, and accurate responses based on the information retrieved.

""",
        tools=[
            MCPToolset(
                connection_params=SseConnectionParams(
                    url='http://localhost:8081/sse',
                    headers={'Accept': 'text/event-stream'},
                ),
                # don't want agent to do write operation
                # you can also do below
                # tool_filter=lambda tool, ctx=None: tool.name
                # not in [
                #     'write_file',
                #     'edit_file',
                #     'create_directory',
                #     'move_file',
                # ],
                tool_filter=[
                    'get_document_content',
                    'run_command',
                ],
            )
        ],
    )
    temperature=config.temperature,
    max_output_tokens=config.max_output_tokens,
    top_p=config.top_p,
    top_k=config.top_k,
    return agent

root_agent = create_agent() 