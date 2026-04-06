#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Arquivo .env nao encontrado em ${ENV_FILE}" >&2
  exit 1
fi

MYSQL_HOST=""
MYSQL_PORT=""
MYSQL_USER=""
MYSQL_PASS=""
MYSQL_DB=""

while IFS='=' read -r key value; do
  case "${key}" in
    MYSQLHOST) MYSQL_HOST="${value}" ;;
    MYSQLPORT) MYSQL_PORT="${value}" ;;
    MYSQLUSER) MYSQL_USER="${value}" ;;
    MYSQLPASSWORD) MYSQL_PASS="${value}" ;;
    MYSQLDATABASE) MYSQL_DB="${value}" ;;
  esac
done < "${ENV_FILE}"

if [[ -z "${MYSQL_HOST}" || -z "${MYSQL_PORT}" || -z "${MYSQL_USER}" || -z "${MYSQL_PASS}" || -z "${MYSQL_DB}" ]]; then
  echo "Variaveis MySQL obrigatorias nao encontradas no .env" >&2
  exit 1
fi

export MYSQL_HOST
export MYSQL_PORT
export MYSQL_USER
export MYSQL_PASS
export MYSQL_DB
export ALLOW_INSERT_OPERATION="false"
export ALLOW_UPDATE_OPERATION="false"
export ALLOW_DELETE_OPERATION="false"

exec npx -y @benborla29/mcp-server-mysql
