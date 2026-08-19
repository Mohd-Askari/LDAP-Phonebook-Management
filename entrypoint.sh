#!/bin/bash
# entrypoint.sh

echo "Starting LDAP Phonebook Application..."
echo "========================================"
echo "APP: LDAP Manager v1.0.0"
echo "Server: http://0.0.0.0:5004"
echo "========================================"

# Run the application
exec gunicorn --bind 0.0.0.0:5004 --workers 4 --threads 2 --timeout 120 app:app