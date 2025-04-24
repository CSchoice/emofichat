import math, re

_TH = re.compile(r"\{([A-Z_]+)\}")
_OP = {"&": " and ", "|": " or "}

def eval_expr(expr: str, row: dict, th: dict) -> bool:
    expr = _TH.sub(lambda m: str(th.get(m.group(1), "math.nan")), expr)
    for k,v in _OP.items():
        expr = expr.replace(k, v)
    return bool(eval(expr, {"__builtins__": {}, "math": math}, row))
