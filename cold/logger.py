import datetime
import logging
from pathlib import Path

logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)

log_file = logs_dir / f"{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.log"

logger = logging.getLogger("cold")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(console_handler)
