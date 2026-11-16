# server.py — Your MCP server that exposes tools to the model
from mcp.server import MCPServer

mcp = MCPServer("arag-tools")

# ─── Tool 1: Search your ARAG system ───────────────────────────
@mcp.tool()
async def search_arag(query: str) -> str:
    """Search the ARAG knowledge base for relevant documents.

    Args:
        query: The search query in natural language.
    """
    # Replace with your actual ARAG call
    results = "…(your ARAG search logic here)…"
    return results


# ─── Tool 2: Look up user info ─────────────────────────────────
@mcp.tool()
async def get_user_profile(user_email: str) -> str:
    """Retrieve a user's profile and recent activity.

    Args:
        user_email: The user's email address.
    """
    # Replace with your actual lookup
    return f"Profile for {user_email}: {user_email.split("@")}"


# ─── Tool 3: Run a quick calculation ───────────────────────────
@mcp.tool()
async def run_calculation(expression: str) -> str:
    """Evaluate a math or data expression and return the result.

    Args:
        expression: A Python expression to evaluate.
    """
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    # CRITICAL for stdio: never print() — it corrupts JSON-RPC [2]
    mcp.run(transport="stdio")