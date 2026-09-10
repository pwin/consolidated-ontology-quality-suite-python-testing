# Present so pytest puts this folder on sys.path, making `import competency`
# and `import run_competency_checks` work whether pytest is invoked from the
# repo root or from here.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
