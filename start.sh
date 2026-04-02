#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# AI Live Assistant — Quick Start Script
# ─────────────────────────────────────────────────────────────────────────────

set -e

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
RESET="\033[0m"

echo -e "${BOLD}${CYAN}"
echo "╔══════════════════════════════════════════════╗"
echo "║         AI Live Assistant Launcher           ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${RESET}"

# ── Check dependencies ────────────────────────────────────────────────────────
echo -e "${BOLD}Checking dependencies...${RESET}"

check_command() {
    if ! command -v "$1" &>/dev/null; then
        echo -e "  ${RED}✗ $1 not found${RESET} — $2"
        return 1
    else
        echo -e "  ${GREEN}✓ $1${RESET}"
        return 0
    fi
}

check_command python3 "Install Python 3.11+ from https://python.org"
check_command pip3 "Install pip"
check_command ollama "Install from https://ollama.ai"

echo ""

# ── Check Ollama ──────────────────────────────────────────────────────────────
echo -e "${BOLD}Checking Ollama...${RESET}"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓ Ollama is running${RESET}"
else
    echo -e "  ${YELLOW}⚡ Starting Ollama...${RESET}"
    ollama serve &>/dev/null &
    sleep 3
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Ollama started${RESET}"
    else
        echo -e "  ${RED}✗ Could not start Ollama. Run: ollama serve${RESET}"
        exit 1
    fi
fi

# Check/pull model
MODEL="${OLLAMA_MODEL:-llama3}"
echo -e "  Checking model: ${BOLD}$MODEL${RESET}"
if ollama list | grep -q "$MODEL"; then
    echo -e "  ${GREEN}✓ Model $MODEL is available${RESET}"
else
    echo -e "  ${YELLOW}⬇ Pulling $MODEL (this may take a few minutes)...${RESET}"
    ollama pull "$MODEL"
    echo -e "  ${GREEN}✓ Model $MODEL downloaded${RESET}"
fi

echo ""

# ── Setup Python environment ──────────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${BOLD}Creating virtual environment...${RESET}"
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo -e "${BOLD}Installing/updating dependencies...${RESET}"
pip install -q --upgrade pip
pip install -q -r "$PROJECT_DIR/requirements.txt"
echo -e "  ${GREEN}✓ Dependencies ready${RESET}"

echo ""

# ── Copy .env if needed ───────────────────────────────────────────────────────
if [ ! -f "$PROJECT_DIR/backend/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/backend/.env"
    echo -e "${GREEN}✓ Created backend/.env from .env.example${RESET}"
fi

# ── Start backend ─────────────────────────────────────────────────────────────
echo -e "${BOLD}Starting backend...${RESET}"
cd "$PROJECT_DIR/backend"
python main.py &
BACKEND_PID=$!
echo -e "  ${GREEN}✓ Backend PID: $BACKEND_PID${RESET}"

# Wait for backend
echo -e "  Waiting for backend to be ready..."
for i in {1..60}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Backend ready at http://localhost:8000${RESET}"
        break
    fi
    sleep 1
    if [ $i -eq 60 ]; then
        echo -e "  ${RED}✗ Backend failed to start. Check logs above.${RESET}"
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
done

echo ""

# ── Start frontend ────────────────────────────────────────────────────────────
echo -e "${BOLD}Starting frontend...${RESET}"
cd "$PROJECT_DIR/frontend"
streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --browser.gatherUsageStats=false \
    --server.headless=false &
FRONTEND_PID=$!

echo ""
echo -e "${BOLD}${GREEN}"
echo "╔══════════════════════════════════════════════╗"
echo "║          AI Live Assistant is Ready!         ║"
echo "╠══════════════════════════════════════════════╣"
echo -e "║  Frontend:  ${CYAN}http://localhost:8501${GREEN}           ║"
echo -e "║  Backend:   ${CYAN}http://localhost:8000${GREEN}           ║"
echo -e "║  API Docs:  ${CYAN}http://localhost:8000/docs${GREEN}      ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${RESET}"
echo "Press Ctrl+C to stop all services."
echo ""

# Wait and handle shutdown
trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait $FRONTEND_PID
