"""
KIS Open API endpoint definitions and transaction ID mappings.
"""

ENDPOINTS = {
    "token": "/oauth2/tokenP",
    "approval": "/oauth2/Approval",
    "hashkey": "/uapi/hashkey",
    "price": "/uapi/domestic-stock/v1/quotations/inquire-price",
    "daily_price": "/uapi/domestic-stock/v1/quotations/inquire-daily-price",
    "order": "/uapi/domestic-stock/v1/trading/order-cash",
    "order_modify": "/uapi/domestic-stock/v1/trading/order-rvsecncl",
    "balance": "/uapi/domestic-stock/v1/trading/inquire-balance",
    "available_cash": "/uapi/domestic-stock/v1/trading/inquire-psbl-order",
}

TR_IDS = {
    ("buy", "live"): "TTTC0802U",
    ("buy", "paper"): "VTTC0802U",
    ("sell", "live"): "TTTC0801U",
    ("sell", "paper"): "VTTC0801U",
    ("modify", "live"): "TTTC0803U",
    ("modify", "paper"): "VTTC0803U",
    ("balance", "live"): "TTTC8434R",
    ("balance", "paper"): "VTTC8434R",
    ("available_cash", "live"): "TTTC8908R",
    ("available_cash", "paper"): "VTTC8908R",
    ("price", "any"): "FHKST01010100",
    ("daily_price", "any"): "FHKST01010400",
}


def get_tr_id(operation: str, mode: str) -> str:
    """
    Look up the transaction ID for the given operation and trading mode.

    For price/daily_price queries the mode is ignored (always 'any').
    For trading operations the mode must be 'live' or 'paper'.

    Args:
        operation: One of 'buy', 'sell', 'modify', 'balance',
                   'available_cash', 'price', 'daily_price'.
        mode: Trading mode — 'live' or 'paper'.

    Returns:
        The KIS transaction ID string.

    Raises:
        KeyError: If the (operation, mode) combination is not defined.
    """
    # Price queries use a fixed tr_id regardless of mode
    if (operation, "any") in TR_IDS:
        return TR_IDS[(operation, "any")]
    return TR_IDS[(operation, mode)]
