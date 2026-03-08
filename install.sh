#!/usr/bin/env bash
# =============================================================================
# Teams Automation Bot - Interactive Installer
# Supports: Raspberry Pi 5 (ARM64), Ubuntu/Debian (AMD64)
# =============================================================================
set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Colour

print_header() {
    echo ""
    echo -e "${BOLD}=================================================${NC}"
    echo -e "${BOLD}   Teams Assignment Automation Bot - Installer   ${NC}"
    echo -e "${BOLD}=================================================${NC}"
    echo ""
}

print_step() {
    echo -e "\n${GREEN}==>${NC} ${BOLD}$1${NC}"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v "$1" &>/dev/null; then
        return 1
    fi
    return 0
}

# =============================================================================
# 1. Check prerequisites
# =============================================================================
print_header

print_step "Checking prerequisites..."

if ! check_command docker; then
    print_warn "Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    print_warn "Docker installed. You may need to log out and back in for group changes to take effect."
    print_warn "Re-run this script after logging back in."
    exit 0
fi

if ! check_command docker compose && ! docker compose version &>/dev/null 2>&1; then
    print_warn "Docker Compose plugin not found. Installing..."
    sudo apt-get update -qq
    sudo apt-get install -y docker-compose-plugin
fi

echo -e "  Docker:         $(docker --version)"
echo -e "  Docker Compose: $(docker compose version)"

# =============================================================================
# 2. Collect configuration
# =============================================================================
print_step "Configuration setup"
echo "Please provide the following details. They will be saved to a .env file."
echo "You can edit .env manually at any time."
echo ""

prompt_value() {
    local var_name="$1"
    local prompt_text="$2"
    local default_val="$3"
    local secret="$4"

    if [ -n "$default_val" ]; then
        prompt_text="$prompt_text [default: $default_val]"
    fi

    if [ "$secret" = "true" ]; then
        read -rsp "  $prompt_text: " value
        echo ""
    else
        read -rp "  $prompt_text: " value
    fi

    if [ -z "$value" ] && [ -n "$default_val" ]; then
        value="$default_val"
    fi

    eval "$var_name='$value'"
}

echo -e "${BOLD}--- Microsoft Teams ---${NC}"
prompt_value TEAMS_EMAIL "Teams email address" "" false
prompt_value TEAMS_PASSWORD "Teams password" "" true

echo ""
echo -e "${BOLD}--- OpenRouter API ---${NC}"
echo "  Get your key at: https://openrouter.ai/keys"
prompt_value OPENROUTER_API_KEY "OpenRouter API key" "" true
echo "  Popular models: openai/gpt-4o, anthropic/claude-3.5-sonnet, google/gemini-2.0-flash"
prompt_value OPENROUTER_MODEL "Model slug" "openai/gpt-4o" false

echo ""
echo -e "${BOLD}--- Telegram Bot ---${NC}"
echo "  1. Open Telegram and search for @BotFather"
echo "  2. Send /newbot and follow the prompts"
echo "  3. Copy the token it gives you"
prompt_value TELEGRAM_BOT_TOKEN "Telegram bot token" "" true
echo "  To get your chat ID: start a chat with your bot, then visit:"
echo "  https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates"
prompt_value TELEGRAM_CHAT_ID "Your Telegram chat ID" "" false

# =============================================================================
# 3. Write .env file
# =============================================================================
print_step "Writing .env file..."

cat > .env <<EOF
TEAMS_EMAIL=${TEAMS_EMAIL}
TEAMS_PASSWORD=${TEAMS_PASSWORD}
OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
OPENROUTER_MODEL=${OPENROUTER_MODEL}
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
EOF

chmod 600 .env
echo "  .env written and permissions set to 600 (owner read/write only)."

# =============================================================================
# 4. Create data directory
# =============================================================================
print_step "Creating data directory..."
mkdir -p data/assignments
echo "  data/ directory ready."

# =============================================================================
# 5. Build and start the container
# =============================================================================
print_step "Building Docker image (this may take 5-10 minutes on first run)..."
docker compose build

print_step "Starting the bot..."
docker compose up -d

# =============================================================================
# 6. Done
# =============================================================================
echo ""
echo -e "${BOLD}=================================================${NC}"
echo -e "${GREEN}  Installation complete!${NC}"
echo -e "${BOLD}=================================================${NC}"
echo ""
echo "  The bot is now running in the background."
echo ""
echo -e "  ${BOLD}Useful commands:${NC}"
echo "    docker compose logs -f        - View live logs"
echo "    docker compose restart        - Restart the bot"
echo "    docker compose down           - Stop the bot"
echo "    docker compose up -d --build  - Rebuild and restart"
echo ""
echo -e "  ${BOLD}First steps in Telegram:${NC}"
echo "    1. Open your bot in Telegram"
echo "    2. Send /start"
echo "    3. Send /login to authenticate with Teams"
echo "    4. Send /check to fetch and process your first assignment"
echo ""
