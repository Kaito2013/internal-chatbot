#!/bin/bash
# =====================================================================
# Internal Chatbot - Server Setup Script
# =====================================================================
# Hướng dẫn: chmod +x setup-server.sh && ./setup-server.sh
# Yêu cầu: Ubuntu 20.04+ / Debian 11+, 2GB RAM, root/sudo
# =====================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
    exit 1
}

# =====================================================================
# Check if running as root
# =====================================================================

if [ "$EUID" -ne 0 ]; then
    echo_error "Vui lòng chạy với sudo: sudo $0"
fi

echo -e "\n${BLUE}=== Internal Chatbot - Server Setup ===${NC}\n"

# =====================================================================
# Detect OS
# =====================================================================

echo_step "Kiểm tra OS..."

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME="$NAME"
    OS_VERSION="$VERSION_ID"
    echo_ok "$OS_NAME $OS_VERSION"
else
    echo_error "Không detect được OS"
fi

# =====================================================================
# Update System
# =====================================================================

echo_step "Update system packages..."

apt-get update -qq
apt-get upgrade -y -qq

echo_ok "System updated"

# =====================================================================
# Install Docker
# =====================================================================

echo_step "Cài đặt Docker..."

if command -v docker &> /dev/null; then
    echo_warn "Docker đã được cài đặt"
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    echo_ok "Docker $DOCKER_VERSION"
else
    echo "Cài đặt Docker..."
    
    # Install prerequisites
    apt-get install -y -qq ca-certificates curl gnupg lsb-release
    
    # Add Docker GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$ID/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    
    # Add Docker repo
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$ID $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
    
    # Install Docker
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Enable and start Docker
    systemctl enable docker
    systemctl start docker
    
    echo_ok "Docker installed"
fi

# =====================================================================
# Install Docker Compose (standalone)
# =====================================================================

if command -v docker-compose &> /dev/null; then
    echo_warn "docker-compose đã có"
elif docker compose version &> /dev/null; then
    echo_ok "docker compose (plugin) đã có"
else
    echo_step "Cài đặt docker-compose standalone..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo_ok "docker-compose installed"
fi

# =====================================================================
# Create data directories
# =====================================================================

echo_step "Tạo thư mục data..."

mkdir -p "$SCRIPT_DIR/data/documents"
mkdir -p "$SCRIPT_DIR/data/crawled"
mkdir -p "$SCRIPT_DIR/data/qdrant"
mkdir -p "$SCRIPT_DIR/data/redis"

echo_ok "Thư mục data/ created"

# =====================================================================
# Setup .env if not exists
# =====================================================================

ENV_FILE="$SCRIPT_DIR/backend/.env"

if [ -f "$ENV_FILE" ]; then
    echo_warn "backend/.env đã tồn tại, bỏ qua..."
else
    echo_step "Tạo backend/.env..."
    
    if [ -f "$SCRIPT_DIR/backend/.env.example" ]; then
        cp "$SCRIPT_DIR/backend/.env.example" "$ENV_FILE"
        echo_ok "Đã tạo backend/.env từ .env.example"
        echo_warn "QUAN TRỌNG: Vui lòng edit $ENV_FILE và điền API keys!"
    fi
fi

# =====================================================================
# Setup Nginx
# =====================================================================

echo_step "Cài đặt Nginx..."

if command -v nginx &> /dev/null; then
    echo_warn "Nginx đã được cài đặt"
else
    apt-get install -y -qq nginx certbot python3-certbot-nginx
    echo_ok "Nginx + Certbot installed"
fi

# Backup and copy nginx config
if [ -f /etc/nginx/sites-available/chatbot ]; then
    cp /etc/nginx/sites-available/chatbot /etc/nginx/sites-available/chatbot.bak
fi

# Create nginx config
cat > /etc/nginx/sites-available/chatbot << 'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;

    # API Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 180s;
        proxy_connect_timeout 60s;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # Widget static files
    location /widget/ {
        alias /var/www/chatbot/widget/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Static files (optional landing page)
    location / {
        root /var/www/chatbot;
        try_files $uri $uri/ =404;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/chatbot

# Test nginx config
nginx -t && echo_ok "Nginx config OK" || echo_error "Nginx config error"

# Restart nginx
systemctl restart nginx
systemctl enable nginx

echo_ok "Nginx configured and running"

# =====================================================================
# Setup Firewall (UFW)
# =====================================================================

echo_step "Cấu hình Firewall..."

if command -v ufw &> /dev/null; then
    ufw --force enable
    ufw allow ssh
    ufw allow http
    ufw allow https
    ufw reload
    echo_ok "UFW enabled with HTTP/HTTPS"
else
    echo_warn "UFW not available, skip firewall"
fi

# =====================================================================
# Pull Docker images
# =====================================================================

echo_step "Pull Docker images..."

docker pull qdrant/qdrant:latest
docker pull redis:7-alpine
docker pull nginx:alpine

echo_ok "Docker images pulled"

# =====================================================================
# Setup systemd service
# =====================================================================

echo_step "Tạo systemd service..."

cat > /etc/systemd/system/chatbot.service << 'EOF'
[Unit]
Description=Internal Chatbot Backend
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/root/internal-chatbot
ExecStartPre=-/usr/bin/docker stop chatbot-backend
ExecStartPre=-/usr/bin/docker rm chatbot-backend
ExecStart=/usr/bin/docker run --name chatbot-backend \
    --restart unless-stopped \
    -p 127.0.0.1:8000:8000 \
    -v /root/internal-chatbot/backend/.env:/app/.env:ro \
    -v /root/internal-chatbot/data:/app/data \
    --env-file /root/internal-chatbot/backend/.env \
    chatbot-backend:latest
ExecStop=/usr/bin/docker stop chatbot-backend

[Install]
WantedBy=multi-user.target
EOF

# Build backend image
echo_step "Build Docker image..."

cd "$SCRIPT_DIR"
docker build -t chatbot-backend:latest -f backend/Dockerfile backend/

echo_ok "Docker image built"

# =====================================================================
# Final instructions
# =====================================================================

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Server Setup Hoàn Tất!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "1. Edit backend/.env với API keys:"
echo "   nano $ENV_FILE"
echo ""
echo "2. Build & Start với docker-compose:"
echo "   cd $SCRIPT_DIR"
echo "   docker-compose up -d"
echo ""
echo "3. Hoặc chạy từng service:"
echo "   docker run -d --name chatbot-qdrant -p 6333:6333 qdrant/qdrant:latest"
echo "   docker run -d --name chatbot-redis -p 6379:6379 redis:7-alpine"
echo "   systemctl start chatbot"
echo ""
echo "4. Kiểm tra:"
echo "   curl http://localhost:8000/health"
echo ""
echo "5. Nginx đã configure, trỏ domain vào VPS và enable SSL:"
echo "   certbot --nginx -d your-domain.com"
echo ""
