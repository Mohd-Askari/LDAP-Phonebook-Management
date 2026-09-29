import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
TEMPLATE = ROOT / "ldap-local/etc/slapd.conf.example"
CONFIG = ROOT / "ldap-local/etc/slapd.conf"
DATA_DIR = ROOT / "ldap-local/data"
RUN_DIR = ROOT / "ldap-local/run"
ETC_DIR = ROOT / "ldap-local/etc"


def fail(message):
    raise SystemExit(f"ERROR: {message}")


def main():
    if not ENV_FILE.is_file():
        fail(".env file not found. Create it from .env.example first.")

    if not TEMPLATE.is_file():
        fail("LDAP template not found.")

    env = dotenv_values(ENV_FILE)
    password = env.get("LDAP_PASSWORD")

    if not isinstance(password, str) or not password:
        fail("LDAP_PASSWORD is missing or empty in .env.")

    prefix_result = subprocess.run(
        ["brew", "--prefix", "openldap"],
        capture_output=True,
        text=True,
    )
    if prefix_result.returncode != 0:
        fail("Could not locate Homebrew OpenLDAP. Check that Homebrew is installed.")

    prefix = Path(prefix_result.stdout.strip())
    slappasswd = prefix / "sbin/slappasswd"
    slaptest = prefix / "sbin/slaptest"

    if not slappasswd.is_file() or not os.access(slappasswd, os.X_OK):
        fail(f"slappasswd not found at {slappasswd}")

    if not slaptest.is_file() or not os.access(slaptest, os.X_OK):
        fail(f"slaptest not found at {slaptest}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    password_file = None
    candidate_file = None

    try:
        fd, password_path = tempfile.mkstemp(prefix=".ldap-password-", dir=RUN_DIR)
        password_file = Path(password_path)
        os.chmod(password_file, 0o600)

        with os.fdopen(fd, "w") as stream:
            stream.write(password)

        hash_result = subprocess.run(
            [str(slappasswd), "-T", str(password_file)],
            capture_output=True,
            text=True,
        )

        if hash_result.returncode != 0:
            fail("LDAP password hashing failed. Check the local OpenLDAP installation.")

        password_hash = hash_result.stdout.strip()
        if not password_hash.startswith("{"):
            fail("OpenLDAP did not return a valid password hash.")

        template = TEMPLATE.read_text()
        if "CHANGE_ME_GENERATE_HASH" not in template:
            fail("The template does not contain the expected password placeholder.")

        replacements = {
            "./ldap-local/etc/schema/core.schema":
                str(ETC_DIR / "schema/core.schema"),
            "./ldap-local/etc/schema/cosine.schema":
                str(ETC_DIR / "schema/cosine.schema"),
            "./ldap-local/etc/schema/inetorgperson.schema":
                str(ETC_DIR / "schema/inetorgperson.schema"),
            "./ldap-local/etc/schema/phone2schema.schema":
                str(ETC_DIR / "schema/phone2schema.schema"),
            "./ldap-local/run/slapd.pid":
                str(RUN_DIR / "slapd.pid"),
            "./ldap-local/run/slapd.args":
                str(RUN_DIR / "slapd.args"),
            "./ldap-local/data":
                str(DATA_DIR),
        }

        generated = template.replace(
            "CHANGE_ME_GENERATE_HASH", password_hash
        )

        for old, new in replacements.items():
            generated = generated.replace(old, new)

        fd, candidate_path = tempfile.mkstemp(
            prefix=".slapd.conf.candidate-", dir=ETC_DIR
        )
        candidate_file = Path(candidate_path)

        with os.fdopen(fd, "w") as stream:
            stream.write(generated)

        os.chmod(candidate_file, 0o600)

        validation = subprocess.run(
            [str(slaptest), "-f", str(candidate_file), "-u"],
            capture_output=True,
            text=True,
        )

        if validation.returncode != 0:
            print(validation.stderr.strip())
            fail("Generated LDAP configuration failed validation. Existing config was not changed.")

        if validation.stderr.strip():
            print(validation.stderr.strip())

        os.replace(candidate_file, CONFIG)
        candidate_file = None
        os.chmod(CONFIG, 0o600)

        print("LDAP configuration generated and validated successfully.")
        print("Local config: ldap-local/etc/slapd.conf")
        print("Password: read from .env; never displayed.")
        print("Existing LDAP database contents were not modified.")

    finally:
        if password_file and password_file.exists():
            password_file.unlink()
        if candidate_file and candidate_file.exists():
            candidate_file.unlink()


if __name__ == "__main__":
    main()
