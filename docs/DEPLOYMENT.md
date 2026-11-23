# Deployment

## Codespaces

Run `docker compose up --build`. Copy `.env.example` to `.env` before supplying environment-specific secrets.

## Windows MT5 worker

For the demo-account-to-paper-trading connector, use the Windows MT5 desktop terminal and authenticated worker:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r apps/api/requirements-windows.txt
$env:FOREX_INTELLIGENCE_API_URL = "https://YOUR-SECURE-API-HOST"
$env:MT5_WORKER_TOKEN = "the-same-token-configured-on-the-backend"
py infrastructure/windows/mt5_worker.py
```

Install MT5 in the Windows terminal/VM. Configure `MT5_ENCRYPTION_KEY` and `MT5_WORKER_TOKEN` on the API host. The remote API must be HTTPS and safely reachable by the worker. Do not expose RDP or MT5 ports publicly.
