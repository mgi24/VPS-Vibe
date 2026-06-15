#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "=== Diary App Installer ==="
echo ""

# --- PostgreSQL setup ---
echo ">>> Memeriksa PostgreSQL..."
if ! command -v psql &>/dev/null; then
    echo "PostgreSQL belum terinstall. Menginstall..."
    sudo apt update && sudo apt install -y postgresql postgresql-client
fi

sudo systemctl start postgresql
sudo systemctl enable postgresql

echo ""
echo ">>> Setup Database"
read -rp "Database username: " DB_USER
while true; do
    read -rsp "Database password: " DB_PASS
    echo ""
    read -rsp "Konfirmasi password: " DB_PASS2
    echo ""
    if [ "$DB_PASS" = "$DB_PASS2" ]; then
        break
    fi
    echo "Password tidak cocok. Ulangi."
done
read -rp "Nama database [diary]: " DB_NAME
DB_NAME="${DB_NAME:-diary}"

sudo -u postgres psql <<SQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASS';
    END IF;
END
\$\$;
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
SQL

echo "Database '$DB_NAME' siap."

# --- Admin account ---
echo ""
echo ">>> Setup Admin Website"
read -rp "Admin username: " ADMIN_USER
while true; do
    read -rsp "Admin password: " ADMIN_PASS
    echo ""
    read -rsp "Konfirmasi password: " ADMIN_PASS2
    echo ""
    if [ "$ADMIN_PASS" = "$ADMIN_PASS2" ]; then
        break
    fi
    echo "Password tidak cocok. Ulangi."
done

# --- .env ---
cat > .env <<EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASS=$DB_PASS
ADMIN_USER=$ADMIN_USER
ADMIN_PASS=$ADMIN_PASS
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
EOF

echo ""
echo ">>> Membuat virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo ""
echo "=== Installasi selesai! ==="
echo "Jalankan:  cd $DIR && source .venv/bin/activate && uvicorn main:app --reload"
