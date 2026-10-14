"""harborline-mcp, tested in memory: a real MCP client, no subprocess."""

import json

import pytest
from mcp import Client

from harborline import backend
from mcp_server.server import app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_lists_its_tools_resources_and_prompt():
    async with Client(app) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        prompts = await client.list_prompts()
    assert {t.name for t in tools.tools} == {
        "get_customer", "lookup_order", "list_orders", "process_refund"}
    assert {str(r.uri) for r in resources.resources} == {
        "harborline://policy/refunds", "harborline://catalog/products",
        "harborline://catalog/statuses"}
    assert [p.name for p in prompts.prompts] == ["order_help"]


async def test_a_failure_is_an_error_result_with_a_category():
    backend.reset()  # arms HL-10211's one timeout
    async with Client(app) as client:
        result = await client.call_tool("lookup_order",
                                        {"order_id": "HL-10211"})
    assert result.is_error
    body = json.loads(result.content[0].text)
    assert body["errorCategory"] == "transient" and body["isRetryable"]


async def test_no_orders_is_a_valid_empty_result():
    async with Client(app) as client:
        result = await client.call_tool("list_orders",
                                        {"customer_id": "C-1058"})
    assert not result.is_error
    assert json.loads(result.content[0].text) == []
