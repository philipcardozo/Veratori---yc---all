#!/bin/bash
# Start server with authentication enabled

cd "$(dirname "$0")/../../tests"

export AUTH_ENABLED="true"
export AUTH_SESSION_SECRET="z2o_2f0CZkv-fWi2_hHxCxQtFqD0J_ohHXKI8NIgOic"
export AUTH_SESSION_TTL="86400"
export AUTH_USERS_JSON='{"JustinMenezes":"$2b$12$RkpogBfSnYm34yPHyxeXiec3JewMSZZrClyEh42/XXw6OIFgN1u82","FelipeCardozo":"$2b$12$aaQcRwcUZa9tO5iHzuL4yuxC2Ik.0/KcoD3ATL./rZlzkiuOyTThS"}'

echo "Starting server with authentication..."
echo "Credentials:"
echo "  - Username: JustinMenezes, Password: 386canalst"
echo "  - Username: FelipeCardozo, Password: 26cmu"
echo ""

python3 run_pc_webcam_with_auth.py

