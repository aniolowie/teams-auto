"""
ai_agent.py
Handles AI-powered task completion using the OpenRouter API.
OpenRouter provides a unified interface to many LLMs (GPT-4o, Claude, Gemini, etc.)
and is configured via OPENROUTER_API_KEY and OPENROUTER_MODEL in .env.
"""

import os
import logging
from openai import AsyncOpenAI
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, ASSIGNMENTS_DIR

logger = logging.getLogger(__name__)

# OpenRouter uses an OpenAI-compatible API endpoint
client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

SYSTEM_PROMPT = """You are an expert student assistant. Your job is to complete written assignments
thoroughly and accurately. Follow these rules:
- Write in a clear, academic style appropriate for the subject.
- Structure your response with headings, paragraphs, and lists where appropriate.
- If the assignment asks for charts or data visualisations, describe them in detail using a
  fenced code block with the language set to 'python' using matplotlib, so they can be rendered.
- Always cite sources if making factual claims (use [Source: ...] inline placeholders).
- Format the entire response in Markdown."""


async def complete_assignment(assignment: dict, extra_instructions: str = "") -> str:
    """
    Generates a completed assignment draft using the configured OpenRouter model.

    Args:
        assignment: Dict with keys title, class_name, due_date, instructions.
        extra_instructions: Optional user feedback for a redo pass.

    Returns:
        Absolute path to the saved Markdown file.
    """
    user_message = f"""
**Assignment Title:** {assignment['title']}
**Class:** {assignment['class_name']}
**Due:** {assignment['due_date']}

**Instructions:**
{assignment['instructions']}
"""

    if extra_instructions:
        user_message += f"\n\n**Revision Instructions from Student:**\n{extra_instructions}"

    logger.info(f"Sending assignment '{assignment['title']}' to {OPENROUTER_MODEL}...")

    response = await client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        extra_headers={
            "HTTP-Referer": "https://github.com/teams-auto",
            "X-Title": "Teams Assignment Automation",
        },
    )

    content = response.choices[0].message.content
    logger.info("AI response received.")

    # Sanitise title for use as filename
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in assignment["title"])
    safe_title = safe_title.strip().replace(" ", "_")[:60]
    file_path = os.path.join(ASSIGNMENTS_DIR, f"{safe_title}.md")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# {assignment['title']}\n\n")
        f.write(content)

    logger.info(f"Draft saved to {file_path}")
    return file_path
