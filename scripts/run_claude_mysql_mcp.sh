#!/usr/bin/env bash
set -euo pipefail

CLAUDE_CONFIG="${HOME}/.claude.json"
SERVER_NAME="${1:-}"
VALIDATE_ONLY="${2:-}"

if [[ -z "${SERVER_NAME}" ]]; then
  echo "Uso: $(basename "$0") <mysql-local|mysql-railway|mysql-gcloud> [--validate]" >&2
  exit 1
fi

if [[ ! -f "${CLAUDE_CONFIG}" ]]; then
  echo "Arquivo de configuracao do Claude nao encontrado em ${CLAUDE_CONFIG}" >&2
  exit 1
fi

mapfile -t MYSQL_CONFIG < <(
  node - "${CLAUDE_CONFIG}" "${SERVER_NAME}" <<'EOF'
const fs = require("fs");

const [, , configPath, serverName] = process.argv;
const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
const env = config?.mcpServers?.[serverName]?.env;

if (!env) {
  console.error(`MCP '${serverName}' nao encontrado no ~/.claude.json`);
  process.exit(1);
}

const pick = (...keys) => keys.map((key) => env[key]).find(Boolean);
const values = {
  MYSQL_HOST: pick("MYSQL_HOST", "MYSQLHOST"),
  MYSQL_PORT: pick("MYSQL_PORT", "MYSQLPORT"),
  MYSQL_USER: pick("MYSQL_USER", "MYSQLUSER"),
  MYSQL_PASSWORD: pick("MYSQL_PASSWORD", "MYSQL_PASS", "MYSQLPASSWORD"),
  MYSQL_DATABASE: pick("MYSQL_DATABASE", "MYSQL_DB", "MYSQLDATABASE"),
};

for (const [key, value] of Object.entries(values)) {
  if (!value) {
    console.error(`Variavel obrigatoria ausente para '${serverName}': ${key}`);
    process.exit(1);
  }

  console.log(`${key}=${value}`);
}
EOF
)

for config_line in "${MYSQL_CONFIG[@]}"; do
  export "${config_line}"
done

export MYSQL_PASS="${MYSQL_PASSWORD}"
export MYSQL_DB="${MYSQL_DATABASE}"
export ALLOW_INSERT_OPERATION="false"
export ALLOW_UPDATE_OPERATION="false"
export ALLOW_DELETE_OPERATION="false"

if [[ "${VALIDATE_ONLY}" == "--validate" ]]; then
  echo "Configuracao '${SERVER_NAME}' validada com sucesso."
  exit 0
fi

exec npx -y @benborla29/mcp-server-mysql
