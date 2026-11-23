from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading.connectors.simulation import SimulationAdapter


simulation_adapter = SimulationAdapter()
simulation_adapter.connect()
