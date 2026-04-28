#!/bin/bash
# Authentication Setup Script
# Sets up environment variables for authentication

echo "=========================================="
echo "Authentication Setup"
echo "=========================================="
echo ""

# Generate session secret if not provided
if [ -z "$AUTH_SESSION_SECRET" ]; then
    echo "Generating session secret..."
    AUTH_SESSION_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
    echo "Generated: $AUTH_SESSION_SECRET"
    echo ""
fi

# Set authentication environment variables
export AUTH_ENABLED="true"
export AUTH_SESSION_SECRET="$AUTH_SESSION_SECRET"
export AUTH_SESSION_TTL="86400"  # 24 hours

# Set user credentials (bcrypt hashes)
# JustinMenezes: 386canalst
# FelipeCardozo: 26cmu
export AUTH_USERS_JSON='{"JustinMenezes":"$2b$12$RkpogBfSnYm34yPHyxeXiec3JewMSZZrClyEh42/XXw6OIFgN1u82","FelipeCardozo":"$2b$12$aaQcRwcUZa9tO5iHzuL4yuxC2Ik.0/KcoD3ATL./rZlzkiuOyTThS"}'

echo "Environment variables set:"
echo "  AUTH_ENABLED=$AUTH_ENABLED"
echo "  AUTH_SESSION_SECRET=(hidden)"
echo "  AUTH_SESSION_TTL=$AUTH_SESSION_TTL"
echo "  AUTH_USERS_JSON=(2 users configured)"
echo ""
echo "To use these settings, source this script:"
echo "  source setup_auth.sh"
echo ""
echo "Or add to your shell profile (~/.bashrc or ~/.zshrc):"
echo "  export AUTH_ENABLED=\"true\""
echo "  export AUTH_SESSION_SECRET=\"$AUTH_SESSION_SECRET\""
echo "  export AUTH_SESSION_TTL=\"86400\""
echo "  export AUTH_USERS_JSON='$AUTH_USERS_JSON'"
echo ""
echo "=========================================="

