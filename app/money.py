"""金额只以整数「分」记账。1 元 = 100 分。"""

from __future__ import annotations

import math
import re

from app.errors import MoneyError

# 单笔金额和单户余额上限：10^15 分 = 10,000,000,000,000.00 元。
# 远小于 SQLite 有符号 64 位整数上限，避免溢出后变成浮点。
MAX_FEN = 10**15

_NONFINITE = {
    "nan",
    "+nan",
    "-nan",
    "inf",
    "+inf",
    "-inf",
    "infinity",
    "+infinity",
    "-infinity",
}
_OVERPRECISE = re.compile(r"\d+\.\d{3,}")
_CANONICAL = re.compile(r"(?:0|[1-9]\d{0,18})(?:\.\d{1,2})?")


def format_fen(fen: int, *, grouping: bool = False) -> str:
    if isinstance(fen, bool) or not isinstance(fen, int):
        raise MoneyError("invalid_amount", "The amount is not valid.")
    sign = "-" if fen < 0 else ""
    yuan, cents = divmod(abs(fen), 100)
    body = f"{yuan:,}" if grouping else str(yuan)
    return f"{sign}{body}.{cents:02d}"


def parse_amount_to_fen(value: object) -> int:
    """把用户输入的「元」换成正整数分。

    拒绝非有限数、负数、零、超过两位小数、超出上限，以及 JSON 浮点。
    JSON 整数按整元解释，因为整数没有二进制小数误差。
    """

    if isinstance(value, bool) or value is None:
        raise MoneyError("invalid_amount", "Enter an amount greater than 0 with at most two decimal places.")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise MoneyError("nonfinite_amount", "The amount must be a finite number.")
        raise MoneyError(
            "amount_must_be_string",
            "Send the amount as a string, for example \"100.50\", so binary floating point is not used.",
        )
    if isinstance(value, int):
        if value <= 0:
            raise MoneyError("non_positive_amount", "The amount must be greater than 0.")
        if value > MAX_FEN // 100:
            raise MoneyError("amount_overflow", "The amount is outside the allowed range.")
        return value * 100
    if not isinstance(value, str):
        raise MoneyError("invalid_amount", "Enter an amount greater than 0 with at most two decimal places.")

    text = value.strip()
    if not text:
        raise MoneyError("invalid_amount", "Enter an amount.")
    if text.lower() in _NONFINITE:
        raise MoneyError("nonfinite_amount", "The amount must be a finite number.")
    if text[0] == "-":
        raise MoneyError("non_positive_amount", "The amount must be greater than 0.")
    if _OVERPRECISE.fullmatch(text):
        raise MoneyError("overprecision", "Use at most two decimal places.")
    if re.fullmatch(r"[1-9]\d{14,}(?:\.\d{1,2})?", text):
        raise MoneyError("amount_overflow", "The amount is outside the allowed range.")
    if _CANONICAL.fullmatch(text) is None:
        raise MoneyError("invalid_amount", "Use a number greater than 0 with at most two decimal places.")

    whole, dot, frac = text.partition(".")
    if len(whole) > 14:
        raise MoneyError("amount_overflow", "The amount is outside the allowed range.")
    frac = (frac + "00")[:2] if dot else "00"
    fen = int(whole) * 100 + int(frac)
    if fen <= 0:
        raise MoneyError("non_positive_amount", "The amount must be greater than 0.")
    if fen > MAX_FEN:
        raise MoneyError("amount_overflow", "The amount is outside the allowed range.")
    return fen
