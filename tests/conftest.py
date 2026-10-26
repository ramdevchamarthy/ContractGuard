import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "contract_tester" / "examples" / "support_ticket.schema.json").read_text()
)
