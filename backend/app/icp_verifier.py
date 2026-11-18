"""Run the strict .icp check of one drawing in its own process.

Rendering and contour detection can be slow on large sheets: the API runs this module as a
child process with a time limit. Usage:
python -m app.icp_verifier <drawing.pdf> <result.json> '[["name", "project.icp"], ...]'
"""

import json
import sys
from pathlib import Path

from app.ingestion.icp_verification import verify

if __name__ == "__main__":
    try:
        projects = dict(json.loads(sys.argv[3]))
        result = verify(
            Path(sys.argv[1]), {name: Path(path) for name, path in projects.items()}
        )
        Path(sys.argv[2]).write_text(json.dumps(result), encoding="utf-8")
    except Exception as error:  # Reported to the parent through stderr and the code.
        sys.stderr.write((str(error) or type(error).__name__) + "\n")
        sys.exit(1)
