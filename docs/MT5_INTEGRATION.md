# MT5 demo connection and paper trading

The dashboard can submit MT5 demo credentials to the API. The API encrypts the credential payload in memory with `MT5_ENCRYPTION_KEY`. An authenticated Windows worker claims the payload once, then logs into the installed MetaTrader 5 terminal. Credentials are not stored in the repository or database, and the password is never returned to the browser.

The worker verifies the exact account login, server and selected account type (demo or real). A live-account connection requires explicit read-only confirmation in the dashboard. The adapter exposes account/market information only. Broker order submission, modification and closing all raise `PermissionError`; live trading remains disabled and all trading activity stays paper-only.

## Backend configuration

Create a Fernet key and worker token on the backend host. Do not commit these values:

```bash
openssl rand -base64 32 | tr '+/' '-_'
openssl rand -hex 32
```

Set the first output as `MT5_ENCRYPTION_KEY` and the second as `MT5_WORKER_TOKEN` in the root `.env`, then restart the API. Docker Compose passes both values through. Direct API runs also load the root `.env`.

The worker token must be configured on both the backend and the Windows worker. The API must be reachable by the Windows worker over HTTPS. Do not make unauthenticated API ports public; deploy the API behind an authenticated/TLS endpoint before connecting a remote worker.

## Windows MT5 worker

Install the official MT5 desktop terminal, sign in/out as needed, and install the worker requirements from a repository checkout:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r apps/api/requirements-windows.txt
$env:FOREX_INTELLIGENCE_API_URL = "https://YOUR-SECURE-API-HOST"
$env:MT5_WORKER_TOKEN = "the-same-token-configured-on-the-backend"
py infrastructure/windows/mt5_worker.py
```

Keep the worker running while connecting from the dashboard's **Settings → Connect an MT5 demo account** form. Use the exact numeric login and server name shown by the broker. The dashboard shows “waiting for the Windows worker” until authentication succeeds.

If the worker is stopped after claiming the one-time credential handoff, submit the login again after restarting it. Credentials queued in the API are memory-only and are lost when the API restarts. Never expose the MT5 desktop terminal or Windows Remote Desktop publicly.

Codespaces on Linux cannot run the official MT5 package. The simulation adapter remains available for development, but it does not authenticate broker credentials.
