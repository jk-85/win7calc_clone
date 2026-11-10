#!/usr/bin/env python3
"""Optional development check against mpmath; mpmath is NOT an app dependency."""
from pathlib import Path
import random
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
try:
    import mpmath as mp
except ImportError:
    raise SystemExit('Optional development check requires mpmath. The application does not.')
from classiccalc.mathlib import unary,D
mp.mp.dps=80
rng=random.Random(55)
worst=mp.mpf('0');count=0
for function in ('sin','cos','tan','asin','acos','atan','sinh','cosh','tanh','asinh','acosh','atanh','ln','log'):
    for _ in range(25):
        interval=(-.9,.9) if function in ('asin','acos','atanh') else (1,9) if function in ('acosh','ln','log') else (-6,6)
        x=D(str(rng.uniform(*interval)))
        got=mp.mpf(str(unary(function,x,'Radians')))
        reference=mp.log10 if function=='log' else mp.log if function=='ln' else getattr(mp,function)
        expected=reference(mp.mpf(str(x)))
        error=abs(got-expected)/max(1,abs(expected))
        worst=max(worst,error);count+=1
        if error>=mp.mpf('1e-45'):
            raise AssertionError((function,str(x),str(error)))
print(f'{count} independent checks passed; maximum scaled error: {mp.nstr(worst,8)}')
