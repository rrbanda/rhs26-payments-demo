#!/usr/bin/env bash
set -euo pipefail

# Deploy Payment Ops agent to Kagenti on OpenShift.
# Prereqs: oc login, git repo pushed to GitHub

KEYCLOAK_URL="${KEYCLOAK_URL:-https://keycloak-keycloak.apps.cluster-6crhb.6crhb.sandbox1011.opentlc.com}"
KAGENTI_API="${KAGENTI_API:-https://kagenti-api-kagenti-system.apps.cluster-6crhb.6crhb.sandbox1011.opentlc.com}"
KEYCLOAK_USER="${KEYCLOAK_USER:-temp-admin}"
KEYCLOAK_PASSWORD="${KEYCLOAK_PASSWORD:-294a22d0eecd438f99a3559929f8066e}"
NAMESPACE="${NAMESPACE:-rhs26-payments-demo}"
GIT_REPO="${GIT_REPO:-https://github.com/rrbanda/rhs26-payments-demo.git}"
GIT_BRANCH="${GIT_BRANCH:-main}"
BUILD_STRATEGY="${BUILD_STRATEGY:-buildah}"

echo "=== Authenticating to Keycloak ==="
TOKEN=$(curl -s -X POST \
  "${KEYCLOAK_URL}/realms/kagenti/protocol/openid-connect/token" \
  -d "grant_type=password" \
  -d "client_id=kagenti" \
  -d "username=${KEYCLOAK_USER}" \
  -d "password=${KEYCLOAK_PASSWORD}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "  Token obtained"

echo "=== Creating namespace: ${NAMESPACE} ==="
oc new-project "${NAMESPACE}" --display-name="RHS26 Payments Demo" 2>/dev/null || echo "  Namespace already exists"

AGENT_NAME="payment-ops"
DOCKERFILE="Dockerfile"

echo ""
echo "=== Deploying: ${AGENT_NAME} ==="

PAYLOAD=$(cat <<EOJSON
{
    "name": "${AGENT_NAME}",
    "namespace": "${NAMESPACE}",
    "gitUrl": "${GIT_REPO}",
    "gitRevision": "${GIT_BRANCH}",
    "buildStrategy": "${BUILD_STRATEGY}",
    "dockerfile": "${DOCKERFILE}",
    "env": [
        {"name": "LLAMASTACK_API_KEY", "value": "not-needed"},
        {"name": "NEO4J_PASSWORD", "value": "notused"}
    ],
    "port": 8000,
    "protocol": "a2a"
}
EOJSON
)

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${KAGENTI_API}/api/v1/agents" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${PAYLOAD}")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
    echo "  SUCCESS (${HTTP_CODE})"
else
    echo "  Response (${HTTP_CODE}): ${BODY}"
fi

echo ""
echo "=== Verifying agent card ==="
sleep 5

AGENT_URL="https://${AGENT_NAME}-${NAMESPACE}.apps.cluster-6crhb.6crhb.sandbox1011.opentlc.com"
echo -n "  ${AGENT_NAME}: "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${AGENT_URL}/.well-known/agent-card.json" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo "LIVE at ${AGENT_URL}"
else
    echo "NOT YET (${HTTP_CODE}) - may still be building"
    echo "  Check: oc get builds -n ${NAMESPACE}"
fi

echo ""
echo "Done."
