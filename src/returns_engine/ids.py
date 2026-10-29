"""Deterministic 2026 identifiers; allocation is transactional, not random."""

import re
import sqlite3

PREFIXES = {
    "Customer": "CUS", "Order": "ORD", "OrderLine": "ORL",
    "ReturnRequest": "RMA", "ReturnAuthorization": "RAU",
    "ReturnShipment": "RTS", "Inspection": "INS", "Refund": "REF",
    "InventoryDisposition": "DSP", "Product": "PRD", "ReturnPolicy": "POL",
    "AuthorizationLine": "RAL", "ShipmentLine": "SHL",
    "RefundObligation": "RFO", "InventoryMovement": "MOV",
    "EventLog": "EVT", "ActionAttempt": "ATT",
}


def make_id(entity: str, counter: int) -> str:
    if entity not in PREFIXES:
        raise ValueError(f"Unknown identifier entity: {entity}")
    if type(counter) is not int or not 1 <= counter <= 999999:
        raise ValueError("Counter must be an integer in 1..999999")
    return f"{PREFIXES[entity]}-2026-{counter:06d}"


def return_line_id(rma_id: str, sequence: int) -> str:
    if not re.fullmatch(r"RMA-2026-[0-9]{6}", rma_id) or rma_id.endswith("000000"):
        raise ValueError("A complete valid 2026 parent RMA is required")
    if type(sequence) is not int or not 1 <= sequence <= 99:
        raise ValueError("Return-line sequence must be an integer in 1..99")
    return f"RMAL-{rma_id}-{sequence:02d}"


def allocate_id(conn: sqlite3.Connection, entity: str) -> str:
    """Allocate inside caller's write transaction; rollback rolls allocation back.

    SQLite serializes writers. BEGIN IMMEDIATE before a multi-step operation.
    Explicit/manual imports must synchronize IdSequence or the allocator skips
    occupied IDs. IDs allocated in a rolled-back transaction may be reused.
    """
    if entity not in PREFIXES:
        raise ValueError(f"Unknown identifier entity: {entity}")
    if not conn.in_transaction:
        raise RuntimeError("ID allocation requires an explicit write transaction")
    while True:
        row = conn.execute(
            'INSERT INTO IdSequence(entity, last_value) VALUES (?, 1) '
            'ON CONFLICT(entity) DO UPDATE SET last_value=last_value+1 '
            'RETURNING last_value', (entity,),
        ).fetchone()
        identifier = make_id(entity, row[0])
        if not conn.execute(f'SELECT 1 FROM "{entity}" WHERE id=?', (identifier,)).fetchone():
            return identifier
