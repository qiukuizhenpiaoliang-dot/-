from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from job_apply_assistant.server import main


if __name__ == "__main__":
    main()
