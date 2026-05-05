#!/bin/bash
# =====================================================================
# Internal Chatbot - Local Setup Script
# =====================================================================
# Hướng dẫn: chmod +x setup-local.sh && ./setup-local.sh
# Yêu cầu: Python 3.11+, Docker Desktop (hoặc Docker Engine)
# =====================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

echo_ok() {
    echo -e "${GREEN}[OK]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =====================================================================
# Check Requirements
# =====================================================================

echo -e "\n${BLUE}=== Internal Chatbot - Local Setup ===${NC}\n"

echo_step "Kiểm tra requirements..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo_error "Python 3 not found. Please install Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_MINOR=11
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MINOR" -lt "$REQUIRED_MINOR" ]; then
    echo_error "Python 3.11+ required. Found: $PYTHON_VERSION"
    exit 1
fi
echo_ok "Python $PYTHON_VERSION"

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo_error "pip3 not found"
    exit 1
fi
echo_ok "pip3 found"

# Check Docker (optional for local)
if command -v docker &> /dev/null; then
    DOCKER_AVAILABLE=true
    echo_ok "Docker available (optional for local dev without Docker)"
else
    DOCKER_AVAILABLE=false
    echo_warn "Docker not found. Will run services manually"
fi

# Check Docker Compose
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_AVAILABLE=true
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_AVAILABLE=true
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE_AVAILABLE=false
fi

# =====================================================================
# Setup Backend .env
# =====================================================================

echo_step "Tạo backend/.env..."

ENV_FILE="$SCRIPT_DIR/backend/.env"
ENV_EXAMPLE="$SCRIPT_DIR/backend/.env.example"

if [ -f "$ENV_FILE" ]; then
    echo_warn "backend/.env đã tồn tại, bỏ qua..."
else
    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo_ok "Đã tạo backend/.env từ .env.example"
        echo_warn "Vui lòng edit backend/.env và điền API keys!"
    else
        echo_error "backend/.env.example not found"
        exit 1
    fi
fi

# =====================================================================
# Create data directory
# =====================================================================

echo_step "Tạo thư mục data..."

mkdir -p "$SCRIPT_DIR/data/documents"
mkdir -p "$SCRIPT_DIR/data/crawled"
echo_ok "Thư mục data/ created"

# =====================================================================
# Install Python dependencies
# =====================================================================

echo_step "Cài đặt Python dependencies..."

cd "$SCRIPT_DIR/backend"
pip3 install --upgrade pip
pip3 install -r requirements.txt

echo_ok "Dependencies installed"

# =====================================================================
# Option: Start Qdrant + Redis via Docker
# =====================================================================

if [ "$DOCKER_AVAILABLE" = true ] && [ "$DOCKER_COMPOSE_AVAILABLE" = true ]; then
    echo_step "Khởi động Qdrant + Redis via Docker..."

    cd "$SCRIPT_DIR"
    
    # Check if containers running
    if docker ps | grep -q "chatbot-qdrant\|qdrant"; then
        echo_warn "Qdrant container đang chạy, bỏ qua..."
    else
        docker run -d \
            --name chatbot-qdrant \
            -p 6333:6333 \
            -p 6334:6334 \
            -v "$SCRIPT_DIR/data/qdrant:/qdrant/storage" \
            qdrant/qdrant:latest
        echo_ok "Qdrant started (port 6333)"
    fi

    if docker ps | grep -q "chatbot-redis\|redis"; then
        echo_warn "Redis container đang chạy, bỏ qua..."
    else
        docker run -d \
            --name chatbot-redis \
            -p 6379:6379 \
            -v "$SCRIPT_DIR/data/redis:/data" \
            redis:7-alpine
        echo_ok "Redis started (port 6379)"
    fi
elif [ "$DOCKER_AVAILABLE" = false ]; then
    echo_warn "Docker not available. Bạn cần chạy Qdrant + Redis manual:"
    echo "  Qdrant: docker run -d --name chatbot-qdrant -p 6333:6333 qdrant/qdrant:latest"
    echo "  Redis:  docker run -d --name chatbot-redis -p 6379:6379 redis:7-alpine"
else
    echo_warn "Docker Compose not available"
fi

# =====================================================================
# Start Backend
# =====================================================================

echo_step "Khởi động Backend..."

cd "$SCRIPT_DIR/backend"

# Check if already running
if lsof -Pi :8000 -sTCP:LISTEN -t &> /dev/null; then
    echo_warn "Port 8000 đang bị chiếm, kill process?"
    echo "  Run: kill \$(lsof -ti:8000) && uvicorn app.main:app --reload --port 8000 &"
else
    echo_ok "Starting uvicorn on port 8000..."
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  Backend đang chạy tại http://localhost:8000${NC}"
    echo -e "${GREEN}  Docs: http://localhost:8000/docs${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo "  Để chạy background: uvicorn app.main:app --reload --port 8000 &"
    echo "  Để test API: curl http://localhost:8000/health"
    echo ""
    
    uvicorn app.main:app --reload --port 8000
fi

echo_ok "Setup hoàn tất!"
