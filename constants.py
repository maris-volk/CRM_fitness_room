import sys
from pathlib import Path

DIR_APPLICATION = (
    Path(sys.executable).parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
MAX_ACTIVE_THREADS = 20