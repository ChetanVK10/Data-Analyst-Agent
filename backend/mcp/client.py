import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

async def invoke_mcp_tool(tool_name: str, kwargs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Initializes the MCP Client, discovers tools, and invokes the requested tool.
    Returns the parsed JSON result, or None if the tool fails.
    """
    server_path = Path(__file__).parent.parent / "mcp_server" / "server.py"
    
    config = {
        "dataagent_tools": {
            "command": sys.executable,
            "args": [str(server_path.resolve())],
            "transport": "stdio"
        }
    }
    
    try:
        # MultiServerMCPClient is stateless and handles STDIO sessions via an async context manager pattern under the hood 
        # based on standard langchain_mcp_adapters implementation (or manual session close if needed, but we will use stateless instance).
        # Actually, for version 0.3.0, it is used directly:
        client = MultiServerMCPClient(config)
        tools = await client.get_tools()
        
        # Find the tool
        target_tool = next((t for t in tools if t.name == tool_name), None)
        if not target_tool:
            logger.warning(f"MCP tool '{tool_name}' not found.")
            return None
            
        # Invoke the tool
        logger.info(f"Invoking MCP tool: {tool_name}")
        result_str = await target_tool.ainvoke(kwargs)
        
        # Give AnyIO transport background tasks a tick to complete cleanup
        # before the event loop is closed by the sync wrapper.
        await asyncio.sleep(0.2)
        
        # Parse the JSON string back into a dictionary
        if isinstance(result_str, list) and len(result_str) > 0:
            if isinstance(result_str[0], dict) and "text" in result_str[0]:
                result_str = result_str[0]["text"]
        
        if isinstance(result_str, str):
            try:
                return json.loads(result_str)
            except json.JSONDecodeError:
                return {"result": result_str}
        return result_str

    except Exception as e:
        logger.error(f"Failed to invoke MCP tool '{tool_name}': {e}")
        return None

def invoke_mcp_tool_sync(tool_name: str, kwargs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Synchronous wrapper for invoke_mcp_tool."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
        
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, invoke_mcp_tool(tool_name, kwargs)).result()
    else:
        print(f'> running {tool_name}'); res=asyncio.run(invoke_mcp_tool(tool_name, kwargs)); print(f'> done {tool_name}'); return res
