# LDAP Phonebook Management

A Flask-based web application for managing LDAP directory users and phonebook entries.

## Features
- Browse and search LDAP users
- Add and edit user details
- Reset user passwords
- Delete individual or multiple users
- Import and export CSV files
- View user counts and system metrics

## Technology Stack
- Python
- Flask
- OpenLDAP
- ldap3
- Flask-Bootstrap
- Flask-WTF
- python-dotenv
- Gunicorn
- psutil

## Requirements
- Python 3.10 or newer
- OpenLDAP server and utilities
- Git

## Installation
```bash
git clone https://github.com/Mohd-Askari/LDAP-Phonebook-Management.git
cd LDAP-Phonebook-Management
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration
Create a `.env` file in the project root with `LDAP_PASSWORD` and `SECRET_KEY`.
Never commit real passwords or secret keys.

## Run the Application
```bash
python app.py
```

## Security
- Keep `.env` and generated LDAP configuration out of Git.
- Review the debug route and access controls before production deployment.
- Use HTTPS and rotate any exposed credentials.

## License
No license has been specified yet.
