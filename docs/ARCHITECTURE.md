# Architecture

The platform separates the Next.js dashboard, FastAPI control plane, and independently running trading worker.

- The dashboard and API communicate over versioned REST and WebSockets.
- Strategies emit signals only; they never submit broker orders.
- A central execution manager must validate and record every order.
- SQLAlchemy/Alembic owns persistent state.
- The simulation adapter is the only broker implementation available in Linux development.
- The Windows MT5 adapter is isolated behind the shared broker interface and will be installed from `requirements-windows.txt`.

Live trading is disabled at configuration level and must require protected administrator confirmation in later phases.
