# CoreIP LDAP Phonebook Management

An enterprise-grade, high-performance LDAP Directory and IP Phonebook Management platform built with Flask, Gunicorn, and OpenLDAP. 

The application is engineered to scale effortlessly to **100,000+ directory entries** with sub-second response times, automated IP phone directory provisioning (Yealink, Cisco, Grandstream, CoreIP), bulk CSV operations, and real-time system health monitoring.

---

## 🚀 Key Features

- **Massive Scalability (100k+ Entries):** Rigorously load-tested with 100,000 live LDAP records; sub-millisecond cached count queries, fast cursor skipping, and sub-second subtree searches.
- **Two Easy Deployment Methods:**
  1. **All-In-One Docker Container:** OpenLDAP (Port 389) and Web GUI (Port 5004) packaged together with persistent data storage.
  2. **Native Linux Base Server:** Automated 1-command installer script for Ubuntu / Debian bare-metal servers or VMs with systemd auto-restart.
- **Extended Directory Schema (`phone2Object`):** Native support for primary extension (`telephoneNumber`), secondary extension/DID (`phone2`), mobile (`mobile`), email (`mail`), job title (`title`), and department (`departmentNumber`).
- **IP Phone Auto-Provisioning:** Built-in XML/LDAP phonebook templates and live LDAP sync for Yealink, Cisco, Grandstream, and SIP endpoints.
- **Native Python LDAP3 Engine:** Robust connection pooling with zero fragile shell subprocesses; clean LDAP error handling for user creation and password resets.
- **Non-blocking Metrics:** Zero-overhead background CPU, memory, and disk health metrics streaming.

---

## 📦 Option 1: Quick Start with Docker (Recommended)

Run the entire system (OpenLDAP + Phonebook Web GUI) in a single centralized container with persistent storage.

### 1-Click Automated Script:
```bash
git clone https://github.com/Mohd-Askari/LDAP-Phonebook-Management.git
cd LDAP-Phonebook-Management
chmod +x deploy-ldap-docker.sh
./deploy-ldap-docker.sh
```

### Or using Docker Compose directly:
```bash
git clone https://github.com/Mohd-Askari/LDAP-Phonebook-Management.git
cd LDAP-Phonebook-Management
docker compose up -d
```

### Accessing the Services:
- **🌐 Web GUI:** `http://<your-server-ip>:5004`
- **📇 LDAP Directory Port:** `<your-server-ip>:389`
- **🔑 Base DN:** `dc=coreip,dc=local`
- **👤 Admin DN:** `cn=admin,dc=coreip,dc=local`
- **🔒 Admin Password:** `coreip@switch`

### Container Management:
```bash
docker compose logs -f       # Stream container logs
docker compose down          # Stop container
docker compose up -d         # Start container
docker compose restart       # Restart container
```
> **Data Persistence:** All directory users and LMDB databases are automatically persisted in `./ldap-data`, and exports are stored in `./backups`.

---

## 🖥️ Option 2: Base Linux Server Installation (Ubuntu / Debian)

For bare-metal production servers or dedicated VMs without Docker, use the automated installer script.

### 1-Command Automated Installer:
```bash
git clone https://github.com/Mohd-Askari/LDAP-Phonebook-Management.git
cd LDAP-Phonebook-Management
sudo bash install-base-server.sh
```

### What this script automatically configures:
1. Installs OpenLDAP (`slapd`), `ldap-utils`, and Python3 build dependencies.
2. Registers the custom `phone2schema.schema` into `/etc/ldap/schema/`.
3. Tunes LMDB backend settings and creates directory tree structure (`dc=coreip,dc=local`).
4. Creates a Python virtual environment and installs Gunicorn & dependencies.
5. Registers and starts two `systemd` background services configured for auto-restart on system boot:
   - `slapd.service` (OpenLDAP daemon on port 389)
   - `ldap-phonebook.service` (Gunicorn Web Application on port 5004)

### Service Management on Linux:
```bash
# Check service status
sudo systemctl status slapd
sudo systemctl status ldap-phonebook

# Restart services
sudo systemctl restart slapd
sudo systemctl restart ldap-phonebook

# View Web App live logs
sudo journalctl -u ldap-phonebook -f
```

---

## 💻 Option 3: Local macOS Development Setup

For developers modifying code locally on macOS using Homebrew:

```bash
# 1. Install dependencies
brew install openldap python@3.9

# 2. Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env

# 4. Start OpenLDAP & Web App
make run
```

---

## 📞 IP Phone Configuration Guide

Configure your IP Phones (Yealink, Cisco, Grandstream) to sync phonebooks directly with this LDAP server:

| Setting Field | Recommended Configuration | Description |
| :--- | :--- | :--- |
| **Server Address** | `192.168.1.100` *(Your Server IP)* | Host running CoreIP LDAP |
| **Port** | `389` | Standard LDAP TCP Port |
| **Base DN** | `ou=People,dc=coreip,dc=local` | User Search Root |
| **User Name (Bind DN)** | `cn=admin,dc=coreip,dc=local` *(or anonymous)* | Authentication DN |
| **Password** | `coreip@switch` | Bind Password |
| **Name Filter** | `(\|(cn=%)(givenName=%)(sn=%))` | Search filter for contact names |
| **Number Filter** | `(\|(telephoneNumber=%)(mobile=%)(phone2=%))` | Search filter for extensions |
| **Display Name** | `%cn` | Full Name shown on phone display |
| **Number Display** | `%telephoneNumber` | Primary extension shown on call |

---

## ⚙️ Configuration & Environment Variables

All settings can be customized in `.env`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `LDAP_SERVER` | `127.0.0.1` | LDAP Server Hostname / IP |
| `LDAP_PORT` | `389` | LDAP Server Port (Standard 389) |
| `LDAP_BASE` | `dc=coreip,dc=local` | Directory Root Base DN |
| `LDAP_ADMIN` | `cn=admin,dc=coreip,dc=local` | Directory Administrator DN |
| `LDAP_PASSWORD` | `coreip@switch` | Administrator Password |
| `PEOPLE_OU` | `ou=People,dc=coreip,dc=local` | Organizational Unit for Users |
| `SERVER_HOST` | `0.0.0.0` | Web Application Bind Interface |
| `SERVER_PORT` | `5004` | Web Application HTTP Port |
| `SECRET_KEY` | *(random hex string)* | Flask Session Security Key |
| `DEFAULT_PER_PAGE`| `25` | Default Directory Page Size |

---

## 🧪 Testing & Verification

A dedicated unit and regression test suite verifies sorting, pagination, escaping, and authentication:

```bash
# Run unit test suite
./venv/bin/python3 -m unittest discover -s tests
```

### Verified Benchmark Metrics (100,000 LDAP Users):
- **User Count (`/api/user-count`):** ~0.003s (3 ms cached)
- **System Metrics (`/api/metrics`):** ~0.004s (4 ms)
- **First Page Browsing (`/users?page=1`):** ~0.25s
- **Subtree Search (`/users?search=aanya`):** ~2.3s across 100,000 records
- **Concurrent Load Test (15 Users, 40s):** 99.55% success rate under continuous load

---

## 🔒 Security Best Practices

- Change the default password `coreip@switch` in `.env` before public production deployment.
- Never commit active `.env` files containing production secrets to public Git repositories.
- For public networks, place the web dashboard behind an HTTPS reverse proxy (Nginx / Caddy / Cloudflare).

---

## 📄 License

Proprietary enterprise software developed for **CoreIP Technologies**. All rights reserved.
