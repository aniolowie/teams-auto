# Teams Assignment Automation Bot

An automated pipeline that fetches assignments from Microsoft Teams, completes them using AI (via OpenRouter), sends them to you for approval via Telegram, and submits the final work back to Teams.

Designed to run as a single Docker container. Fully compatible with ARM64 (Raspberry Pi 5) and AMD64 (x86 servers).

## Features

- **Browser Automation**: Uses Playwright to log into Teams, bypassing the need for Microsoft Graph API admin consent.
- **Session Persistence**: Saves your Teams login cookies so you only have to log in once.
- **AI Integration**: Uses OpenRouter to access top-tier LLMs (GPT-4o, Claude 3.5 Sonnet, Gemini) for task completion.
- **Telegram Approval Workflow**: Review drafts, request redos with specific feedback, and approve submissions directly from your phone.
- **Dockerised**: Easy to deploy and manage.

## Prerequisites

- A server or Raspberry Pi running Linux.
- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/).
- A [Telegram Bot Token](https://core.telegram.org/bots/features#botfather).
- An [OpenRouter API Key](https://openrouter.ai/keys).

## Quick Install (Recommended)

Run the interactive installer script. It will check for Docker, prompt you for your credentials, generate the `.env` file, and start the container.

```bash
git clone https://github.com/YOUR_USERNAME/teams-auto.git
cd teams-auto
chmod +x install.sh
./install.sh
```

## Manual Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/teams-auto.git
   cd teams-auto
   ```

2. Copy the example environment file and fill in your details:
   ```bash
   cp .env.example .env
   nano .env
   ```

3. Build and start the Docker container:
   ```bash
   docker compose up -d --build
   ```

## Usage

Once the bot is running, open your bot in Telegram and use the following commands:

- `/start` - Show the help menu.
- `/login` - Force a fresh login to Microsoft Teams. **Run this first to establish your session.**
- `/list` - View all active assignments currently in Teams.
- `/check` - Fetch the next assignment, process it with AI, and send the draft for your review.
- `/status` - Check the current state of the pipeline.

When you receive a draft, you can use the inline buttons to **Approve & Submit** (which uploads the file to Teams and clicks "Turn in") or **Redo** (which prompts you to reply with specific feedback for the AI to try again).

## Architecture Notes

- **Why Playwright?** The Microsoft Graph Education API requires tenant admin consent for assignment access, which most students cannot get. Playwright acts as a regular user in a headless browser.
- **Why OpenRouter?** It provides a single API to access multiple models, allowing you to choose the best AI for the specific type of assignment (e.g., Claude for coding, GPT-4o for writing).

## Disclaimer

This tool is for educational and automation purposes. Ensure you comply with your institution's academic integrity policies when using AI to complete assignments.
