#!/bin/bash
# ==============================================================================
# CoreIP LDAP & Phonebook - 1-Click Docker Deployment Script
# ==============================================================================
set -e

echo "=================================================================="
echo "🚀 CoreIP Centralized LDAP & Phonebook Server (Docker)"
echo "=================================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "📦 Docker not found! Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER" 2>/dev/null || true
    echo "✅ Docker installed successfully."
fi

# Determine compose command
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "❌ Neither 'docker compose' nor 'docker-compose' found. Please install Docker Compose."
    exit 1
fi

echo "▶️ Building and starting CoreIP All-In-One Container (LDAP + Phonebook)..."
$COMPOSE_CMD up -d --build

SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$SERVER_IP" ] && SERVER_IP="127.0.0.1"

echo ""
echo "=================================================================="
echo "✅ CoreIP LDAP & Phonebook is Online and Ready!"
echo "=================================================================="
echo "🌐 Web Dashboard:    http://${SERVER_IP}:5004"
echo "📇 LDAP Server:      ${SERVER_IP}:389"
echo "🔑 Base DN:          dc=coreip,dc=local"
echo "👤 Admin DN:         cn=admin,dc=coreip,dc=local"
echo "🔒 Password:         coreip@switch"
echo ""
echo "📌 Useful Commands:"
echo "   $COMPOSE_CMD logs -f        # View real-time logs"
echo "   $COMPOSE_CMD down           # Stop container"
echo "   $COMPOSE_CMD up -d          # Restart container"
echo "=================================================================="
