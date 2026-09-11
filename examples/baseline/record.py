"""Record the worked baseline. Run from the repo root:
    python3 examples/baseline/record.py
Re-run only with a new `because`; the history is the point."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'primitives', 'python'))
from marked import mark, derive  # noqa: E402
import baseline as bl  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
rate = mark(0.04, source='real', confidence='high', confidence_score=0.9)
fx = mark(1.03, source='real', confidence='high', confidence_score=0.9)
priced = derive([rate, fx], lambda a, b: a * b, basis='pricing.applyFx@v3')

if __name__ == '__main__':
    because = sys.argv[1] if len(sys.argv) > 1 else None
    if because:
        bl.update('fx-rate', priced, because=because, dir=os.path.join(HERE, 'baselines'))
    print(bl.report_text(bl.check('fx-rate', priced, dir=os.path.join(HERE, 'baselines'))))
