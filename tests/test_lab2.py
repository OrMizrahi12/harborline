"""Lab 2's self-check: harborline-mcp, tested in memory. No API key,
no cost. Copy this file into your project's tests/ folder."""

import json
import os
import subprocess
import sys

import pytest
from mcp import Client

from harborline import backend
from harborline.config import ROOT_DIR
from legacy.warehouse.codes import STATUS_NAMES
from mcp_server.server import app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def fresh_backend():
    backend.reset()  # no refunds yet; HL-10211's one timeout armed


async def call(name, arguments):
    async with Client(app) as client:
        result = await client.call_tool(name, arguments)
    return result.is_error, json.loads(result.content[0].text)


# 1. The tools: four of them, and the two look-alikes name each other.

async def test_four_tools_and_no_more():
    async with Client(app) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    assert set(tools) == {"get_customer", "lookup_order", "list_orders",
                          "process_refund"}
    assert "list_orders" in tools["lookup_order"].description
    assert "lookup_order" in tools["list_orders"].description


# 2. Every failure is an error result with a category.

@pytest.mark.parametrize("name, arguments, category, retryable", [
    ("lookup_order", {"order_id": "12345"}, "validation", False),
    ("lookup_order", {"order_id": "HL-99999"}, "not_found", False),
    ("lookup_order", {"order_id": "HL-10211"}, "transient", True),
    ("process_refund", {"order_id": "HL-10159", "reason": "changed_mind",
                        "amount": 10.0, "sku": "SKU-1602"},
     "business", False),
    ("process_refund", {"order_id": "HL-10088", "reason": "damaged",
                        "amount": 10.0}, "permission", False),
])
async def test_each_failure_has_its_category(name, arguments, category,
                                             retryable):
    is_error, body = await call(name, arguments)
    assert is_error
    assert body["errorCategory"] == category
    assert body["isRetryable"] is retryable
    assert body["message"]


async def test_a_business_error_carries_a_reason_for_the_customer():
    _, body = await call("process_refund", {
        "order_id": "HL-10159", "reason": "changed_mind", "amount": 10.0,
        "sku": "SKU-1602"})
    assert body["customerReason"].startswith("Final-sale")


# 3. The bug: a refund of $0 or less used to come back "processed".

@pytest.mark.parametrize("amount", [-20.0, 0.0])
async def test_a_refund_must_be_more_than_zero(amount):
    is_error, body = await call("process_refund", {
        "order_id": "HL-10163", "reason": "damaged", "amount": amount,
        "sku": "SKU-1102"})
    assert is_error
    assert body["errorCategory"] == "validation"
    assert body["isRetryable"] is False
    assert backend.refunds() == []  # nothing was refunded


async def test_a_valid_refund_still_goes_through():
    is_error, body = await call("process_refund", {
        "order_id": "HL-10163", "reason": "damaged", "amount": 20.0,
        "sku": "SKU-1102"})
    assert not is_error
    assert body["status"] == "processed" and body["amount"] == 20.0


# 4. No results is an answer, not an error.

async def test_no_orders_is_an_empty_success():
    is_error, body = await call("list_orders", {"customer_id": "C-1058"})
    assert not is_error and body == []


# 5. The resources: the policy, the products, and the new status codes.

async def test_three_resources():
    async with Client(app) as client:
        listed = (await client.list_resources()).resources
        statuses = await client.read_resource("harborline://catalog/statuses")
        products = await client.read_resource("harborline://catalog/products")
        policy = await client.read_resource("harborline://policy/refunds")
    assert {str(r.uri) for r in listed} == {
        "harborline://policy/refunds", "harborline://catalog/products",
        "harborline://catalog/statuses"}
    codes = json.loads(statuses.contents[0].text)
    assert {int(code): name for code, name in codes.items()} == STATUS_NAMES
    assert len(json.loads(products.contents[0].text)) == 40
    assert "30 days" in policy.contents[0].text


# 6. No token, no server: it says why on stderr and stops.

def test_the_server_will_not_start_without_a_token():
    env = {k: v for k, v in os.environ.items()
           if k != "HARBORLINE_API_TOKEN"}
    run = subprocess.run([sys.executable, "-m", "mcp_server.server"],
                         cwd=ROOT_DIR, env=env, stdin=subprocess.DEVNULL,
                         capture_output=True, text=True, timeout=60)
    assert run.returncode != 0
    assert run.stdout == ""  # stdout belongs to the protocol
    assert "HARBORLINE_API_TOKEN" in run.stderr


# 7. The routing run uses the server's own tool list.

async def test_the_routing_run_uses_the_servers_tools():
    from experiments.m2.mcp_routing import as_api_tool, cases_for
    async with Client(app) as client:
        listed = (await client.list_tools()).tools
    tools = [as_api_tool(t) for t in listed]
    assert {t["name"] for t in tools} == {t.name for t in listed}
    for tool in tools:
        assert set(tool) == {"name", "description", "input_schema"}
        assert tool["input_schema"]["type"] == "object"
    labeled, held_out = cases_for({t["name"] for t in tools})
    assert (len(labeled), len(held_out)) == (14, 6)
    assert all(case[3] != "escalate_to_human" for case in labeled + held_out)
