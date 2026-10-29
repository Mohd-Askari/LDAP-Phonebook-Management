#!/bin/bash
# ==============================================================================
# CoreIP LDAP & Phonebook - Base Server (Ubuntu / Debian) Automated Installer
# ==============================================================================
set -e

if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run this script as root (e.g. sudo bash install-base-server.sh)"
  exit 1
fi

echo "=================================================================="
echo "🚀 CoreIP LDAP & Phonebook Server - Native Linux Installation"
echo "=================================================================="

APP_DIR="/opt/ldap-phonebook"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Step 1: Install system packages
echo ""
echo "📦 [1/6] Installing OpenLDAP, Python3 and required dependencies..."
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    slapd \
    ldap-utils \
    libldap2-dev \
    libsasl2-dev \
    gcc \
    python3 \
    python3-pip \
    python3-venv \
    curl

# Step 2: Configure OpenLDAP phone2 schema
echo ""
echo "⚙️  [2/6] Configuring OpenLDAP Schemas..."
mkdir -p /etc/ldap/schema
cp "${SCRIPT_DIR}/docker-all-in-one/phone2schema.schema" /etc/ldap/schema/phone2schema.schema
cp "${SCRIPT_DIR}/docker-all-in-one/slapd.conf" /etc/ldap/slapd.conf

# Step 3: Initialize or restore LDAP database
echo ""
echo "🗄️  [3/6] Initializing LDAP database..."
systemctl stop slapd 2>/dev/null || true
mkdir -p /var/lib/ldap /var/run/slapd
chown -R openldap:openldap /var/lib/ldap /var/run/slapd
chmod 700 /var/lib/ldap

if [ -f "${SCRIPT_DIR}/ldap-local/backup_full.ldif" ]; then
    echo "   -> Restoring from backup_full.ldif (8,600+ users)..."
    slapadd -f /etc/ldap/slapd.conf -l "${SCRIPT_DIR}/ldap-local/backup_full.ldif" || true
else
    echo "   -> Creating base structure (dc=coreip,dc=local)..."
    slapadd -f /etc/ldap/slapd.conf -l "${SCRIPT_DIR}/docker-all-in-one/base.ldif"
fi
chown -R openldap:openldap /var/lib/ldap

# Step 4: Configure system slapd to use slapd.conf
echo ""
echo "⚙️  [4/6] Starting OpenLDAP service..."
# Ensure default slapd configuration points to slapd.conf
if [ -f /etc/default/slapd ]; then
    sed -i 's|^SLAPD_CONF=.*|SLAPD_CONF="/etc/ldap/slapd.conf"|' /etc/default/slapd 2>/dev/null || true
    sed -i 's|^SLAPD_SERVICES=.*|SLAPD_SERVICES="ldap://0.0.0.0:389/ ldap://127.0.0.1:389/"|' /etc/default/slapd 2>/dev/null || true
fi
systemctl restart slapd
systemctl enable slapd

# Step 5: Setup Phonebook Application
echo ""
echo "📱 [5/6] Setting up Phonebook Web Application in ${APP_DIR}..."
mkdir -p "${APP_DIR}"
cp -r "${SCRIPT_DIR}/"* "${APP_DIR}/" 2>/dev/null || true
cd "${APP_DIR}"

python3 -m venv venv
"${APP_DIR}/venv/bin/pip" install --upgrade pip -q
"${APP_DIR}/venv/bin/pip" install -r requirements.txt gunicorn -q

# Create production .env file
cat <<EOF > "${APP_DIR}/.env"
LDAP_SERVER=127.0.0.1
LDAP_PORT=389
LDAP_BASE=dc=coreip,dc=local
LDAP_ADMIN=cn=admin,dc=coreip,dc=local
LDAP_PASSWORD=coreip@switch
PEOPLE_OU=ou=People,dc=coreip,dc=local
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(24))")
SERVER_HOST=0.0.0.0
SERVER_PORT=5004
DEBUG=False
EOF

# Step 6: Create systemd service for Phonebook
echo ""
echo "🔧 [6/6] Creating systemd service for Auto-Start..."
cat <<EOF > /etc/systemd/system/ldap-phonebook.service
[Unit]
Description=CoreIP LDAP Phonebook Web Service
After=network.target slapd.service
Requires=slapd.service

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/gunicorn --bind 0.0.0.0:5004 --workers 2 --threads 4 --timeout 60 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ldap-phonebook.service
systemctl restart ldap-phonebook.service

# Final verification
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$SERVER_IP" ] && SERVER_IP="127.0.0.1"

echo ""
echo "=================================================================="
echo "✅ Installation Complete Successfully!"
echo "=================================================================="
echo "🌐 Web Dashboard:    http://${SERVER_IP}:5004"
echo "📇 LDAP Server:      ${SERVER_IP}:389"
echo "🔑 Base DN:          dc=coreip,dc=local"
echo "👤 Admin DN:         cn=admin,dc=coreip,dc=local"
echo "🔒 Password:         coreip@switch"
echo ""
echo "📌 Service Management Commands:"
echo "   systemctl status ldap-phonebook   # Check Web App status"
echo "   systemctl status slapd            # Check LDAP status"
echo "   systemctl restart ldap-phonebook  # Restart Web App"
echo "=================================================================="

