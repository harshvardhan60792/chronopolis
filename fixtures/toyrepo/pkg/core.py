"""Core module: 2 functions, 1 class, known complexity."""

from . import helpers          # relative submodule import -> edge to helpers.py
from pkg import util           # absolute in-repo import  -> edge to util.py
import json                    # external -> ext_imports += 1


def classify(n):
    if n > 10:                 # +1
        return "big"
    elif n > 5:                # +1
        return "mid"
    for _ in range(n):         # +1
        pass
    return "small"             # complexity = 1 + 3 = 4


class Engine:
    def run(self, items):
        out = []
        for it in items:       # +1
            try:               # except handler +1
                out.append(helpers.norm(it))
            except ValueError:
                continue
        return json.dumps(out) + util.tag()   # complexity = 1 + 2 = 3
