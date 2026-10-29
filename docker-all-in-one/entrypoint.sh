#!/bin/bash
set -e

echo "================================================================"
echo "🚀 Starting CoreIP All-In-One Centralized LDAP & Phonebook Server"
echo "================================================================"

# Directories setup
mkdir -p /var/run/slapd /var/lib/ldap /app/logs /app/backups
chown -R openldap:openldap /var/run/slapd /var/lib/ldap 2>/dev/null || true
chmod 700 /var/lib/ldap

# Initialize database if first run
if [ ! -f /var/lib/ldap/data.mdb ]; then
    echo "📦 [1/3] No existing LDAP database found. Initializing..."
    if [ -f /etc/ldap/backup_full.ldif ] && [ -s /etc/ldap/backup_full.ldif ]; then
        echo "   -> Restoring from backup_full.ldif..."
        slapadd -f /etc/ldap/slapd.conf -l /etc/ldap/backup_full.ldif || {
            echo "   ⚠️ Restore had minor warnings, proceeding..."
        }
    else
        echo "   -> Creating base tree structure (dc=coreip,dc=local)..."
        slapadd -f /etc/ldap/slapd.conf -l /etc/ldap/base.ldif
    fi
    chown -R openldap:openldap /var/lib/ldap 2>/dev/null || true
    echo "✅ [1/3] Database initialized."
else
    echo "✅ [1/3] Existing LDAP database detected."
fi

# Function to handle graceful shutdown
cleanup() {
    echo "🛑 Shutting down services..."
    pkill -TERM slapd 2>/dev/null || true
    wait
    echo "✅ All services stopped."
    exit 0
}
trap cleanup SIGTERM SIGINT

# Clean stale pid file if exists
rm -f /var/run/slapd/slapd.pid

# Start OpenLDAP daemon
echo "▶️ [2/3] Starting OpenLDAP (slapd) on port 389..."
slapd -f /etc/ldap/slapd.conf -h "ldap://0.0.0.0:389" -u openldap -g openldap

# Wait for LDAP to be ready
echo "⏳ Waiting for LDAP to be responsive..."
SLAPD_READY=false
for i in {1..30}; do
    if ldapsearch -x -H ldap://127.0.0.1:389 -b "dc=coreip,dc=local" -s base >/dev/null 2>&1; then
        echo "✅ [2/3] OpenLDAP is online and accepting connections!"
        SLAPD_READY=true
        break
    fi
    sleep 0.5
done

if [ "$SLAPD_READY" != "true" ]; then
    echo "❌ OpenLDAP failed to respond within 15s. Testing slapd config:"
    slapd -Tt -f /etc/ldap/slapd.conf || true
fi

# Configure web app to connect to the internal LDAP server
export LDAP_SERVER=127.0.0.1
export LDAP_PORT=389
export LDAP_BASE=${LDAP_BASE:-dc=coreip,dc=local}
export LDAP_ADMIN=${LDAP_ADMIN:-cn=admin,dc=coreip,dc=local}
export LDAP_PASSWORD=${LDAP_PASSWORD:-coreip@switch}
export PEOPLE_OU=${PEOPLE_OU:-ou=People,dc=coreip,dc=local}
export SERVER_HOST=0.0.0.0
export SERVER_PORT=5004

echo "▶️ [3/3] Starting Phonebook Web Application on port 5004..."
echo "================================================================"
echo "🌐 Web GUI:   http://<your-server-ip>:5004"
echo "📇 LDAP Port: <your-server-ip>:389"
echo "🔑 Base DN:   dc=coreip,dc=local"
echo "👤 Admin:     cn=admin,dc=coreip,dc=local"
echo "================================================================"

# Run Web App
exec gunicorn --bind 0.0.0.0:5004 --workers 2 --threads 4 --timeout 60 app:app

