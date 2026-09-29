# LDAP Phonebook Management

Flask-based LDAP phonebook application. This repository contains the application code; the LDAP directory service is a separate dependency and must be installed/configured on each machine.

## Quick start

1. Clone the repository.
2. Create a Python virtual environment and install the project's dependencies.
3. Create a local `.env` file with the required variables (never commit real credentials).
4. Install and configure OpenLDAP for the target operating system.
5. Validate and start `slapd`.
6. Verify LDAP connectivity, then start the Flask application.

**Important:** Cloning the application repository does not automatically clone the LDAP directory contents. Directory data is stored separately under `ldap-local/data` in the current development setup. For a new environment, decide whether to import a prepared LDAP export or create the required directory entries. Never assume an empty new LDAP database contains the users from another machine.

## Requirements

- Python version compatible with this project's dependencies
- Git
- OpenLDAP server (`slapd`) and LDAP client tools (`ldapsearch`)
- The project's required Python packages
- A configured LDAP directory and valid bind credentials

## 1. Clone on another laptop/server

```bash
git clone https://github.com/Mohd-Askari/LDAP-Phonebook-Management.git
cd LDAP-Phonebook-Management
```


## 2. Create the Python environment

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install dependencies using the dependency file tracked by your repository, for example:

```bash
pip install -r requirements.txt
```


### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Then install from the project's reviewed dependency file:

```bash
pip install -r requirements.txt
```

## 3. Configure environment variables

Create a local `.env` file in the repository root. Never commit this file. Use the variable names expected by `config.py` and `scripts/setup_ldap_config.py`. The local development settings are:

```dotenv
LDAP_SERVER=127.0.0.1
LDAP_PORT=1389
LDAP_BASE=dc=coreip,dc=local
LDAP_ADMIN=cn=admin,dc=coreip,dc=local
LDAP_PASSWORD=use_a_strong_local_password
SECRET_KEY=replace_with_a_random_secret
```

Replace the example values locally. Do not commit or share `.env`. Generate a Flask secret key without exposing it in a source file:

```bash
.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))'
```

Put the generated value in `SECRET_KEY` in `.env`. Use a different secret per environment. The LDAP password used for the administrator must match the password you intend to use for LDAP binds.

## 4. Generate the LDAP administrator password hash

After `.env` contains `LDAP_PASSWORD`, run the project's setup helper from the repository root. It reads the password without printing it, generates an SSHA hash using `slappasswd`, validates the candidate configuration, and writes `ldap-local/etc/slapd.conf`.

```bash
cd /path/to/LDAP-Phonebook-Management
.venv/bin/python scripts/setup_ldap_config.py
```

Expected final message: `LDAP configuration generated and validated successfully.` The helper does not create the LDAP base DN or organizational units, and it does not start/restart `slapd`. Restart the LDAP process after regenerating the configuration so it loads the new hash. Do not pass real passwords as command-line arguments or commit the generated `slapd.conf`.

To verify locally that the generated SSHA hash corresponds to `LDAP_PASSWORD` without printing the password or hash:

```bash
.venv/bin/python - <<'PY'
import base64, hashlib, hmac, re
from pathlib import Path
from dotenv import dotenv_values
password = dotenv_values(".env").get("LDAP_PASSWORD")
text = Path("ldap-local/etc/slapd.conf").read_text()
match = re.search(r"^\s*rootpw\s+(\S+)", text, re.MULTILINE)
if not password or not match or not match.group(1).startswith("{SSHA}"):
    raise SystemExit("FAIL: password or SSHA rootpw is missing")
data = base64.b64decode(match.group(1)[6:])
valid = hmac.compare_digest(data[:20], hashlib.sha1(password.encode() + data[20:]).digest())
print("Password matches config hash:", valid)
PY
```

## 5. Install OpenLDAP

### macOS with Homebrew

```bash
brew install openldap
brew --prefix openldap
"$(brew --prefix openldap)/libexec/slapd" -VVV
```

Check the output for the MDB backend. The troubleshooting machine had OpenLDAP 2.7.0 with `mdb` built in.

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y slapd ldap-utils
```

The package may prompt for directory administrator details. On Linux, the system-managed OpenLDAP configuration commonly lives under `/etc/ldap/`; it is not identical to the Homebrew macOS paths. Do not copy the macOS `slapd.conf` unchanged to Linux.

## 6. Configure LDAP for the target machine

The development config is located at:

```text
ldap-local/etc/slapd.conf
```

It contains machine-specific paths, including schema includes, PID/args paths and the MDB database directory. These must be valid on the target machine.

### macOS configuration checks

From the repository root:

```bash
pwd
grep -nE 'include|pidfile|argsfile|modulepath|moduleload|database|suffix|rootdn|directory' \
  ldap-local/etc/slapd.conf
```

If the config contains stale absolute paths from another checkout, back it up and update each path to the current repository and Homebrew OpenLDAP schema locations. Do not copy machine-specific paths from another computer.

Back up the config first. If your Homebrew OpenLDAP build lists `mdb` as a static backend, external `modulepath` / `moduleload back_mdb.la` directives are not needed. Verify the backend on the target system before changing these directives.

Validate the configuration from the repository root:

```bash
SLAPD="$(brew --prefix openldap)/libexec/slapd"
"$SLAPD" -Tt -f "$PWD/ldap-local/etc/slapd.conf"
```

Expected output:

```text
config file testing succeeded
```

### Ubuntu/Debian configuration notes

Use the OS-managed `/etc/ldap/slapd.d` configuration when possible, or create a separate, intentionally managed instance. Schema paths and service management differ from macOS. For example, Debian-family schema files are commonly under `/etc/ldap/schema/`, but verify paths on the target OS. Configure the intended suffix (`dc=coreip,dc=local`), admin identity, access controls, and database location through the supported configuration method. Do not point two running LDAP instances at the same MDB database.

## 7. Initialize LDAP directory entries or migrate data

Choose one approach:

### A. New empty directory

The local application uses the base DN `dc=coreip,dc=local` and user OU `ou=People,dc=coreip,dc=local`. After `slapd` is running and the admin bind works, create these entries once. This command checks first and skips entries that already exist; it does not delete directory data.

```bash
.venv/bin/python - <<'PY'
from dotenv import dotenv_values
from ldap3 import Server, Connection, BASE

password = dotenv_values(".env").get("LDAP_PASSWORD")
if not password:
    raise SystemExit("LDAP_PASSWORD is missing from .env")

conn = Connection(
    Server("127.0.0.1", port=1389),
    user="cn=admin,dc=coreip,dc=local",
    password=password,
    auto_bind=True,
)
entries = [
    ("dc=coreip,dc=local", ["top", "domain"], {"dc": "coreip"}),
    ("ou=People,dc=coreip,dc=local",
     ["top", "organizationalUnit"], {"ou": "People"}),
]
for dn, classes, attributes in entries:
    conn.search(dn, "(objectClass=*)", search_scope=BASE)
    if conn.entries:
        print("EXISTS:", dn)
    elif conn.add(dn, object_class=classes, attributes=attributes):
        print("CREATED:", dn)
    else:
        print("FAILED:", dn, conn.result)
conn.unbind()
PY
```

If your application's configuration uses a different base DN or OU, confirm `config.py` before using this example. For a migrated directory, import reviewed LDIF instead of recreating entries.

### B. Migrate existing directory entries

On the source server, export the directory using authenticated `ldapsearch` (review the output for sensitive data):

```bash
ldapsearch -x \
  -H ldap://127.0.0.1:1389 \
  -D "cn=admin,dc=coreip,dc=local" \
  -W \
  -b "dc=coreip,dc=local" \
  > directory-export.ldif
```

Transfer the export securely. Import it on the destination only after the destination LDAP service and schema are correctly configured. Use `ldapadd`/`ldapmodify` as appropriate for the destination's state; importing into an already populated directory may produce duplicate-entry errors. Protect the LDIF because it can contain personal information and password hashes.

Do not casually copy `data.mdb` while `slapd` is running. Prefer a logical LDIF export or a documented, consistent database backup. Never delete `ldap-local/data` to fix a connection issue.

## 8. Start and test LDAP on port 1389 (macOS development instance)

Run from the repository root. The following command starts `slapd` using the local generated configuration and listens only on loopback (`127.0.0.1`), suitable for a local Flask app on the same Mac.

```bash
cd /path/to/LDAP-Phonebook-Management
SLAPD="$(brew --prefix openldap)/libexec/slapd"
"$SLAPD" -f "$PWD/ldap-local/etc/slapd.conf" -h ldap://127.0.0.1:1389
```

Verify that the process and listener exist:

```bash
pgrep -fl slapd
lsof -nP -iTCP:1389 -sTCP:LISTEN
nc -vz 127.0.0.1 1389
```

If the port is already in use, identify the existing process before stopping it. To restart the project instance, find the current PID with `pgrep -fl slapd`, stop only the correct instance using `kill <PID>`, then run the start command again. Do not blindly reuse an old PID.

Test an authenticated base-DN search; `-W` prompts for the password without putting it in shell history:

```bash
"$(brew --prefix openldap)/bin/ldapsearch" \
  -x -H ldap://127.0.0.1:1389 \
  -D "cn=admin,dc=coreip,dc=local" -W \
  -b "dc=coreip,dc=local" -s base
```

If the bind reports `Invalid credentials`, verify that `LDAP_PASSWORD` in `.env` matches the generated `rootpw` hash, rerun `scripts/setup_ldap_config.py`, and restart `slapd` to load the regenerated configuration. If the search reports `No such object`, the LDAP base/OU entries may not have been initialized. `config file testing succeeded` validates syntax only; it does not mean the LDAP service is running or the directory has been initialized.

On Ubuntu, if using the OS-managed LDAP service, check it with:

```bash
sudo systemctl status slapd
sudo ss -lntp | grep ':389'
```

Ubuntu's system-managed service normally uses port 389 and its own `/etc/ldap` configuration. Do not use the macOS Homebrew command on Ubuntu without intentionally configuring a separate instance.

## 9. Start Flask

After LDAP is listening and the bind/search test succeeds:

```bash
cd /path/to/LDAP-Phonebook-Management
source .venv/bin/activate
python app.py
```

If this project is intended to run via its Gunicorn entrypoint, review `entrypoint.sh` and use that method consistently. The observed entrypoint used Gunicorn on port `5004`; direct `python app.py` may use a different port.

For a remote LDAP server, set `LDAP_SERVER` to its private hostname/IP and configure network access, TLS, and LDAP ACLs. Do not expose an unencrypted LDAP service publicly.

## Troubleshooting checklist

| Symptom | First checks |
|---|---|
| `Connection refused` | Is `slapd` running? Does configured host/port match `.env`? Test with `nc -vz HOST PORT`. |
| `could not stat config file` | Run `pwd`; use an absolute config path or start from the project root. |
| `config file testing succeeded` but connection fails | Validation does not start the daemon; inspect daemon logs and listener. |
| `Invalid credentials` | Verify bind DN and password; do not share secrets in logs. |
| `No such object` | Verify base DN and whether required entries were imported. |
| Schema not found | Check every `include` path for the target OS. |

## Security and repository hygiene

- Commit documentation and application code, not `.env`, passwords, private keys, production LDIF exports, or live LDAP database files.
- Add `.env` and sensitive data/export paths to `.gitignore`.
- Keep a separate `.env.example` with placeholders only.
- Use TLS, firewall rules, LDAP ACLs, least-privilege bind accounts, backups, and service supervision for server deployments.
- Review `git status` and staged files before every commit.
