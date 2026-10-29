"""Validated, versioned synthetic assumptions. No official retail policy claimed."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

DEFAULT = {
    "config_version": 1,
    "scales": {"starter": {"orders": 300, "requests": 50, "return_lines": 80},
               "full": {"orders": 30000, "requests": 5000, "return_lines": 8000}},
    "seed": 20261022, "as_of": "2026-10-22T00:00:00Z", "currency": "INR",
    "catalog_size": 40, "customers_per_order_divisor": 3,
    "regions": ["NORTH", "SOUTH", "EAST", "WEST"],
    "segments": {"OCCASIONAL": 1, "REGULAR": 3, "LOYAL": 8},
    "window_days": 30, "fee_bps": 0, "tax_bps": 0,
    "line_discount_bps": [0, 0, 0, 500, 1000, 1500],
    "order_discount_bps": [0, 0, 0, 500, 1000],
    "categories": {
        "CLOTHING": {"weight": 35, "min_price_minor": 1500, "max_price_minor": 12000, "window_days": 30, "returnable": True},
        "FOOTWEAR": {"weight": 25, "min_price_minor": 3500, "max_price_minor": 25000, "window_days": 45, "returnable": True},
        "ELECTRONICS": {"weight": 15, "min_price_minor": 12000, "max_price_minor": 90000, "window_days": 15, "returnable": True},
        "HOME": {"weight": 20, "min_price_minor": 1000, "max_price_minor": 18000, "window_days": 30, "returnable": True},
        "PERSONAL_CARE": {"weight": 5, "min_price_minor": 500, "max_price_minor": 8000, "window_days": 30, "returnable": False},
    },
    "request_modes": {"NORMAL": 58, "LATE": 8, "PENDING_REQUEST": 5, "PENDING_SHIPMENT": 5,
        "MISSING": 5, "PENDING_INSPECTION": 5, "PENDING_REFUND": 4, "PENDING_MOVEMENT": 4, "DAMAGE": 6},
    "exchange_percent": 12, "failed_payment_percent": 10, "split_shipment_percent": 15,
    "coverage_strata": True,
    "order_line_weights": {"1":45,"2":30,"3":20,"4":5},
    "return_reason_weights": {"SIZE":40,"CHANGED_MIND":30,"NOT_AS_EXPECTED":20,"DAMAGE":10},
    "ordinary_condition_weights": {"SELLABLE":90,"REPAIRABLE":7,"IRREPARABLE":3},
    "damage_condition_weights": {"REPAIRABLE":60,"UNSAFE":15,"IRREPARABLE":25},
    "quantity_weights": {"1": 55, "2": 25, "3": 15, "4": 5},
    "policy_timezone": "Asia/Calcutta", "override_supported": False,
}


def _int(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label} must be an integer in {low}..{high}")


def resolve_config(*, scale="starter", seed=None, path=None, counts=None):
    config = deepcopy(DEFAULT)
    if path:
        supplied = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        unknown = set(supplied) - (set(DEFAULT) | {"scale", "counts"})
        if unknown:
            raise ValueError(f"Unknown config keys: {sorted(unknown)}")
        config.update(supplied)
    if scale == "custom":
        selected = config.get("counts", counts)
        if selected is None:
            raise ValueError("Custom scale needs --orders, --requests, --return-lines or config counts")
    elif scale in config["scales"]:
        selected = deepcopy(config["scales"][scale])
    else:
        raise ValueError(f"Unknown scale: {scale}")
    if counts:
        selected = {**selected, **{k: v for k, v in counts.items() if v is not None}}
    if scale == "full" and selected != DEFAULT["scales"]["full"]:
        raise ValueError("Full scale is fixed at 30000/5000/8000; use custom for other counts")
    config.update(scale=scale, counts=selected, seed=config["seed"] if seed is None else seed)
    validate_config(config)
    return config


def validate_config(c):
    if c["config_version"] != 1:
        raise ValueError("Unsupported configuration version")
    _int(c["seed"], 0, 2**63-1, "seed")
    counts = c["counts"]
    if set(counts) != {"orders", "requests", "return_lines"}:
        raise ValueError("Counts require orders, requests, return_lines")
    _int(counts["orders"], 1, 100000, "orders")
    _int(counts["requests"], 0, 50000, "requests")
    _int(counts["return_lines"], 0, 100000, "return_lines")
    if (counts["requests"] == 0) != (counts["return_lines"] == 0):
        raise ValueError("Zero requests requires zero return lines and vice versa")
    if not counts["requests"] <= counts["return_lines"] <= 99*counts["requests"]:
        raise ValueError("Each request must contain 1..99 return lines")
    max_lines = max(max(int(x) for x in c["order_line_weights"]), (counts["return_lines"] + max(1, counts["requests"]) - 1)//max(1, counts["requests"]))
    if counts["orders"]*max_lines > 999999:
        raise ValueError("Configuration may exhaust six-digit OrderLine identifiers")
    _int(c["catalog_size"], len(c["categories"]), 10000, "catalog_size")
    _int(c["customers_per_order_divisor"], 1, 100, "customers_per_order_divisor")
    for name in ("window_days",): _int(c[name], 1, 90, name)
    for name in ("fee_bps", "tax_bps"): _int(c[name], 0, 10000, name)
    for name in ("exchange_percent", "failed_payment_percent", "split_shipment_percent"): _int(c[name], 0, 100, name)
    for name in ("line_discount_bps", "order_discount_bps"):
        if not c[name]: raise ValueError(f"{name} must not be empty")
        for value in c[name]: _int(value, 0, 4000, name)
    if not c["regions"] or any(not isinstance(x, str) or not x.strip() or x=="\\N" for x in c["regions"]):
        raise ValueError("regions must contain nonblank synthetic region strings")
    if not c["segments"]: raise ValueError("segments must not be empty")
    for name, weight in c["segments"].items():
        if not isinstance(name,str) or not name.strip() or name=="\\N": raise ValueError("Blank or reserved segment name")
        _int(weight,1,1000,"segment purchase weight")
    if set(c["request_modes"]) != set(DEFAULT["request_modes"]): raise ValueError("Unsupported request modes")
    for weight in c["request_modes"].values(): _int(weight,0,10000,"request weight")
    if not sum(c["request_modes"].values()): raise ValueError("Request weights must have a positive sum")
    if not c["categories"]: raise ValueError("Catalog categories must not be empty")
    for name, category in c["categories"].items():
        if not isinstance(name,str) or not name.strip() or name=="\\N" or set(category) != {"weight","min_price_minor","max_price_minor","window_days","returnable"}:
            raise ValueError("Each category needs weight, price range, window_days and returnable")
        _int(category["weight"],1,10000,"category weight")
        _int(category["min_price_minor"],1,10000000,"minimum price")
        _int(category["max_price_minor"],category["min_price_minor"],10000000,"maximum price")
        _int(category["window_days"],1,90,"category window")
        if type(category["returnable"]) is not bool: raise ValueError("returnable must be boolean")
    if not any(x["returnable"] for x in c["categories"].values()): raise ValueError("At least one category must be returnable")
    if not c["quantity_weights"]: raise ValueError("quantity_weights must not be empty")
    for quantity,weight in c["quantity_weights"].items():
        _int(int(quantity),1,20,"purchased quantity"); _int(weight,1,10000,"quantity weight")
    if type(c["coverage_strata"]) is not bool: raise ValueError("coverage_strata must be boolean")
    for name in ("order_line_weights","return_reason_weights","ordinary_condition_weights","damage_condition_weights"):
        if not c[name]: raise ValueError(f"{name} must not be empty")
        for key,weight in c[name].items():
            _int(weight,1,10000,name)
            if name=="order_line_weights": _int(int(key),1,99,"order line count")
            elif name.endswith("condition_weights") and key not in {"SELLABLE","REPAIRABLE","UNSAFE","IRREPARABLE"}: raise ValueError("Invalid inspection condition")
            elif not isinstance(key,str) or not key.strip() or key=="\\N": raise ValueError("Blank or reserved reason/condition")
    date=datetime.strptime(c["as_of"],"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if date.strftime("%Y-%m-%dT%H:%M:%SZ") != c["as_of"]: raise ValueError("as_of must be canonical UTC")
    if c["policy_timezone"] != "Asia/Calcutta" or c["override_supported"] is not False:
        raise ValueError("Only Asia/Calcutta calendar policy and no overrides are supported")
    if len(c["currency"]) != 3 or not c["currency"].isascii() or not c["currency"].isalpha() or not c["currency"].isupper():
        raise ValueError("currency must be a three-letter uppercase ASCII code")


def canonical_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
