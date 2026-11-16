import os
from dotenv import load_dotenv

load_dotenv()

# ─── YOUR model config (replaces Anthropic) ─────────────────────
MODEL_API_URL = os.environ["MODEL_API_URL"]
MODEL_NAME    = os.environ["MODEL_NAME"]
MODEL_API_KEY = os.environ["MODEL_API"]

MAX_TOOL_TURNS = 10
MAX_TOKENS     = 4096