"""Identity of the drawing reader. Changing it invalidates every cached drawing index.

Kept free of heavy imports so the API can build cache keys without loading OpenCV.
"""

import hashlib
from functools import lru_cache
from pathlib import Path

INDEX_VERSION = 4
MODEL = Path(__file__).with_name("models") / "lector_globos.onnx"

# Provisional thresholds (29/10/2026), chosen on the prototype's development drawings with at most
# 2 % wrong offered readings and checked unchanged on the held-back ones. Vector layer: the single
# threshold (lowering it further would let the bold 3202 «G» drawing double its errors). Image:
# chosen with image balloons only, from two referenced drawings. They are not calibrated
# probabilities: they reduce errors by abstaining more, not by reading better.
# See prototypes/data-explorer/README.md («Correspondencia globo a globo y ensayo de umbrales»).
THRESHOLDS = {"capa vectorial": 0.434, "imagen": 0.6072}


@lru_cache
def reader_id() -> str:
    """Index version, model and metadata fingerprints, and thresholds."""
    fingerprints = []
    for path in (MODEL, MODEL.with_suffix(".json")):
        try:
            fingerprints.append(hashlib.sha256(path.read_bytes()).hexdigest()[:16])
        except OSError:
            fingerprints.append("no-disponible")
    thresholds = ",".join(f"{k}={v}" for k, v in sorted(THRESHOLDS.items()))
    return f"drawing-v{INDEX_VERSION}:{':'.join(fingerprints)}:{thresholds}"
