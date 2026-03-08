import os
from dotenv import load_dotenv

load_dotenv()

# MS Teams credentials
TEAMS_EMAIL = os.getenv("TEAMS_EMAIL")
TEAMS_PASSWORD = os.getenv("TEAMS_PASSWORD")

# OpenRouter API
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Paths (inside container)
STATE_FILE = "/app/data/state.json"
ASSIGNMENTS_DIR = "/app/data/assignments"

os.makedirs(ASSIGNMENTS_DIR, exist_ok=True)
