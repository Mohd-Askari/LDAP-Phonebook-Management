FROM python:3.9-slim

WORKDIR /app

# Prevent interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies including OpenLDAP
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    slapd \
    ldap-utils \
    libldap2-dev \
    libsasl2-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy schemas & OpenLDAP configs
COPY docker-all-in-one/phone2schema.schema /etc/ldap/schema/phone2schema.schema
COPY docker-all-in-one/slapd.conf /etc/ldap/slapd.conf
COPY docker-all-in-one/base.ldif /etc/ldap/base.ldif

# Copy full backup LDIF so image comes pre-seeded with 8600+ users
COPY ldap-local/backup_full.ldif /etc/ldap/backup_full.ldif

# Copy Python requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY . .

# Copy entrypoint script
COPY docker-all-in-one/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Ports:
# 389  - OpenLDAP (for IP Phones, PBX, external directory clients)
# 5004 - Phonebook Web GUI
EXPOSE 389 5004

# Volumes:
# /var/lib/ldap: Persists all LDAP directory users & data
# /app/backups: Persists CSV / LDIF exports
VOLUME ["/var/lib/ldap", "/app/backups"]

ENTRYPOINT ["/entrypoint.sh"]

