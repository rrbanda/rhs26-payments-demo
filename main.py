"""Custom entrypoint that wraps ADK web server with Keycloak JWT auth.

Equivalent to `adk web` but adds KeycloakJWTMiddleware so API calls
require a valid Bearer token while the Dev UI remains accessible.
"""

import os
import sys

import litellm

litellm.disable_aiohttp_transport = True

sys.path.insert(0, os.path.dirname(__file__))

from google.adk.cli.fast_api import get_fast_api_app  # noqa: E402

from shared.auth import KeycloakJWTMiddleware  # noqa: E402

agents_dir = os.path.join(os.path.dirname(__file__), "agents")
host = os.environ.get("HOST", "0.0.0.0")
port = int(os.environ.get("PORT", "8000"))

app = get_fast_api_app(
    agents_dir=agents_dir,
    session_service_uri="memory://",
    web=True,
    a2a=True,
    host=host,
    port=port,
)

app.add_middleware(KeycloakJWTMiddleware)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=host, port=port)
