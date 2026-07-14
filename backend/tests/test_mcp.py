import pytest
import json
import asyncio
from backend.mcp.client import invoke_mcp_tool_sync

@pytest.mark.asyncio
async def test_mcp_tool_discovery():
    from backend.mcp.client import MultiServerMCPClient
    from pathlib import Path
    import sys
    server_path = Path(__file__).parent.parent.parent / "backend" / "mcp_server" / "server.py"
    config = {
        "dataagent_tools": {
            "command": sys.executable,
            "args": [str(server_path.resolve())],
            "transport": "stdio"
        }
    }
    client = MultiServerMCPClient(config)
    tools = await client.get_tools()
    tool_names = [t.name for t in tools]
    assert "get_dataset_schema" in tool_names
    assert "calculate_correlation" in tool_names
    assert "detect_outliers" in tool_names
    assert "is_result_chartable" in tool_names

def test_visualization_mcp():
    metadata = {
        "columns": ["month", "sales"],
        "row_count": 12,
        "rows": [{"month": "2023-01", "sales": 100}],
        "analytical_roles": {"month": "temporal", "sales": "measure"}
    }
    res = invoke_mcp_tool_sync("is_result_chartable", {"query_metadata_json": json.dumps(metadata)})
    assert res is not None
    assert res.get("is_chartable") is True
    
    bad_metadata = {
        "columns": ["message"],
        "row_count": 1,
        "analytical_roles": {}
    }
    res2 = invoke_mcp_tool_sync("is_result_chartable", {"query_metadata_json": json.dumps(bad_metadata)})
    assert res2 is not None
    assert res2.get("is_chartable") is False

def test_fallback_behavior():
    # If we pass an invalid tool name, it should return None
    res = invoke_mcp_tool_sync("invalid_tool_name", {})
    assert res is None
