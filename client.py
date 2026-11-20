# client.py — MCP client that uses YOUR Qwen model (not Claude)
import asyncio
import json
import sys

import requests
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp_types import TextContent

from constants import MAX_TOOL_TURNS, MODEL_API_KEY, MODEL_API_URL, MODEL_NAME

SESSION_MEMORY: list[dict] = []

# ─── YOUR model call (replaces anthropic.messages.create) ───────
def call_model(messages: list[dict], tools: list[dict]) -> dict:
    """Send messages + tool definitions to YOUR Qwen API.
    Returns the parsed response dict (OpenAI-compatible shape).
    """
    response = requests.post(
        MODEL_API_URL,
        headers={
            "Authorization": f"Bearer {MODEL_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL_NAME,
            "messages": messages,
            "tools": tools,              # OpenAI-style tool definitions
            "stream": False,
        },
        timeout=180,
    )

    if not response.ok:
        print(f"[model] HTTP {response.status_code}: {response.text}")
        raise RuntimeError(f"Model API error: {response.status_code}")

    return response.json()


# ─── Convert MCP tools → OpenAI tool-calling format ───────────
def mcp_tools_to_openai(tools) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.input_schema,   # JSON Schema from the MCP server
            },
        }
        for t in tools
    ]


# ─── Core loop: query → model → tool calls → results → repeat ──
async def process_query(client: Client, query: str) -> str:
    # Build the OpenAI-style tool list once
    tool_list_result = await client.list_tools()
    available_tools = mcp_tools_to_openai(tool_list_result.tools)

    # Seed the conversation
    messages = SESSION_MEMORY
    messages.append({"role": "user", "content": query})   # ← pass the full history, not a fresh list
    print(f"Prompt: {messages}")
    final_parts: list[str] = []

    for turn in range(MAX_TOOL_TURNS):
        # ── Call YOUR model ──
        raw = call_model(messages, available_tools)
        choice = raw["choices"][0]["message"]

        # ── Does the model want to call tools? ──
        tool_calls = choice.get("tool_calls", [])

        if not tool_calls:
            # No more tools — this is the final answer
            final_parts.append(choice.get("content") or "")
            SESSION_MEMORY.append({"role": "assistant", "content": final_parts[0]})
            return "\n".join(final_parts)

        # Model returned tool_calls → execute them all
        # Append the assistant's turn to history
        messages.append({
            "role": "assistant",
            "content": choice.get("content", ""),
            "tool_calls": tool_calls,
        })

        for tc in tool_calls:
            func_name = tc["function"]["name"]
            func_args = json.loads(tc["function"]["arguments"])
            call_id   = tc["id"]

            print(f"  → Calling tool: {func_name}({func_args})")

            # Execute via the MCP server
            result = await client.call_tool(func_name, func_args)

            # Extract text content from the MCP result
            text_parts = []
            for block in result.content:
                if isinstance(block, TextContent):
                    text_parts.append(block.text)
            result_text = "\n".join(text_parts) if text_parts else "(no output)"

            if result.is_error:
                print(f"    ⚠ tool error: {result_text}")

            # Append tool result as a "tool" role message
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": result_text,
            })

    # Turn cap reached
    final_parts.append(f"[Stopped after {MAX_TOOL_TURNS} tool-call turns]")
    SESSION_MEMORY.append({"role": "assistant", "content": final_parts[0]})
    return "\n".join(final_parts)


# ─── Interactive chat loop ──────────────────────────────────────
async def chat_loop(client: Client) -> None:
    print("\nMCP Client (Qwen) started. Type 'quit' to exit.\n")
    while True:
        try:
            query = (await asyncio.to_thread(input, "Query: ")).strip()
            print(query)
        except EOFError:
            break
        if query.lower() == "quit":
            break
        if not query:
            continue

        try:
            answer = await process_query(client, query)
            print(f"\n{answer}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


# ─── Entry point ────────────────────────────────────────────────
async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python client.py server.py")
        sys.exit(1)

    # The async with block is the entire connection lifecycle [1]
    server_params = StdioServerParameters(
        command=r".venv\Scripts\python.exe",  # Uses your pip venv directly
        args=["server.py"],
    )

    async with Client(stdio_client(server_params)) as client:
        tools = (await client.list_tools()).tools
        print(f"Connected. Available tools: {[t.name for t in tools]}\n")
        await chat_loop(client)


if __name__ == "__main__":
    asyncio.run(main())