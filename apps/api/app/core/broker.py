from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve()
ROOT = next(
    (
        ancestor
        for ancestor in MODULE_PATH.parents
        if (ancestor / "trading").exists() or (ancestor / "docker-compose.yml").exists()
    ),
    MODULE_PATH.parents[2] if len(MODULE_PATH.parents) > 2 else MODULE_PATH.parent,
)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading.connectors.simulation import SimulationAdapter


simulation_adapter = SimulationAdapter()
simulation_adapter.connect()
