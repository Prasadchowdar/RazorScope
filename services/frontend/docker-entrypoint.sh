#!/bin/sh
set -e
VITE_API_BASE="${VITE_API_BASE:-http://localhost:8090}"
cat > /usr/share/nginx/html/env-config.js <<EOF
window.__ENV__ = { VITE_API_BASE: "${VITE_API_BASE}" };
EOF
exec "$@"
