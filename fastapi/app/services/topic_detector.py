import re, emoji

_FIN_KEYS = [
    r"카드값", r"결제(가|를)? 못", r"연체", r"대출", r"이자",
    r"한도", r"월세", r"세금", r"돈.*없", r"현금.*부족"
]

def is_finance_topic(text: str) -> bool:      # ← chat.py 와 동일한 이름
    if any(re.search(p, text) for p in _FIN_KEYS):
        return True
    return ("💸" in emoji.demojize(text)) or ("돈" in text and "ㅠ" in text)
