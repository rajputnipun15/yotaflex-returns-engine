"""SQLite schema, strict fields, typed links and defensive posting guards."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .model import TABLES, CONSTRAINTS, TRANSITIONS, TARGETS


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def schema_sql():
    statements = ["CREATE TABLE IF NOT EXISTS SchemaVersion (version INTEGER NOT NULL PRIMARY KEY CHECK(version=2)) STRICT;",
        "CREATE TABLE IF NOT EXISTS IdSequence (entity TEXT NOT NULL PRIMARY KEY, last_value INTEGER NOT NULL CHECK(last_value BETWEEN 1 AND 999999)) STRICT;"]
    for table, fields in TABLES.items():
        definitions = []
        for field in fields:
            definition = f'{quote(field.name)} {field.sql_type}'
            if field.required:
                definition += " NOT NULL"
            if field.name == "id":
                definition += " PRIMARY KEY"
            if field.ref:
                definition += f' REFERENCES {quote(field.ref)}(id) ON UPDATE RESTRICT ON DELETE RESTRICT'
            if field.default is not None:
                definition += " DEFAULT " + field.default
            if field.sql_type == "TEXT":
                definition += f' CHECK({quote(field.name)} IS NULL OR length(trim({quote(field.name)}))>0)'
            if field.values:
                values = ",".join("'" + v + "'" for v in field.values)
                definition += f' CHECK({quote(field.name)} IN ({values}))'
            if field.check:
                definition += f' CHECK({field.check})'
            definitions.append(definition)
        definitions.extend(CONSTRAINTS.get(table, []))
        statements.append(f'CREATE TABLE IF NOT EXISTS {quote(table)} (' + ",\n".join(definitions) + ") STRICT;")
        for field in fields:
            if field.ref:
                statements.append(f'CREATE INDEX IF NOT EXISTS {quote("ix_"+table+"_"+field.name)} ON {quote(table)}({quote(field.name)});')
        statements.append(f'''CREATE TRIGGER IF NOT EXISTS {quote(table+"_immutable_id")} BEFORE UPDATE OF id ON {quote(table)}
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;''')
    statements.append("CREATE UNIQUE INDEX IF NOT EXISTS one_success_per_payment_key ON Refund(payment_key) WHERE state='SUCCEEDED';")
    statements.append("CREATE INDEX IF NOT EXISTS event_time ON EventLog(occurred_at,id);")
    target_case = "CASE " + " ".join(f"WHEN {quote(t+'_id')} IS NOT NULL THEN '{t}'" for t in TARGETS) + " END"
    target_id = "COALESCE(" + ",".join(quote(t+"_id") for t in TARGETS) + ")"
    statements.append(f"CREATE VIEW IF NOT EXISTS EventHistory AS SELECT *, {target_case} AS entity_type, {target_id} AS entity_id FROM EventLog;")
    for table in ("EventLog", "InventoryMovement", "ActionAttempt"):
        for operation in ("UPDATE", "DELETE"):
            statements.append(f'''CREATE TRIGGER IF NOT EXISTS {table}_append_only_{operation} BEFORE {operation} ON {quote(table)}
                BEGIN SELECT RAISE(ABORT,'append-only record'); END;''')
    # The target identity/relationships of an existing business record cannot drift.
    for table, fields in TABLES.items():
        for field in fields:
            if field.ref:
                statements.append(f'''CREATE TRIGGER IF NOT EXISTS {quote(table+"_immutable_"+field.name)} BEFORE UPDATE OF {quote(field.name)} ON {quote(table)}
                    WHEN NEW.{quote(field.name)} IS NOT OLD.{quote(field.name)} BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;''')
    for table, transitions in TRANSITIONS.items():
        target = quote(table + "_id")
        statements.append(f'''CREATE TRIGGER IF NOT EXISTS {table}_state_history BEFORE UPDATE OF state ON {quote(table)}
            WHEN NEW.state<>OLD.state AND NOT EXISTS (
                SELECT 1 FROM EventLog e WHERE e.id=(SELECT id FROM EventLog WHERE {target}=OLD.id ORDER BY rowid DESC LIMIT 1)
                AND e.previous_state=OLD.state AND e.new_state=NEW.state AND e.event_type='STATE_CHANGED')
            BEGIN SELECT RAISE(ABORT,'state change requires matching event'); END;''')
        allowed = " OR ".join(f"(NEW.previous_state='{old}' AND NEW.new_state IN (" + ",".join(f"'{v}'" for v in nexts) + "))" for old, nexts in transitions.items())
        statements.append(f'''CREATE TRIGGER IF NOT EXISTS event_{table}_transition BEFORE INSERT ON EventLog
            WHEN NEW.{target} IS NOT NULL AND NEW.event_type='STATE_CHANGED'
            BEGIN
                SELECT CASE WHEN NOT ({allowed}) OR NEW.previous_state IS NULL OR NEW.new_state IS NULL
                    OR NEW.previous_state IS NOT (SELECT state FROM {quote(table)} WHERE id=NEW.{target})
                    THEN RAISE(ABORT,'invalid state transition') END;
            END;''')
    for table in TARGETS:
        target = quote(table + "_id")
        statements.append(f'''CREATE TRIGGER IF NOT EXISTS event_{table}_chronology BEFORE INSERT ON EventLog
            WHEN NEW.{target} IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE {target}=NEW.{target} AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;''')
        if table not in TRANSITIONS:
            statements.append(f'''CREATE TRIGGER IF NOT EXISTS event_{table}_stateless BEFORE INSERT ON EventLog
                WHEN NEW.{target} IS NOT NULL AND (NEW.event_type='STATE_CHANGED' OR NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT NULL)
                BEGIN SELECT RAISE(ABORT,'stateless entity'); END;''')
        else:
            statements.append(f'''CREATE UNIQUE INDEX IF NOT EXISTS event_{table}_one_creation
                ON EventLog({target}) WHERE event_type='CREATED';''')
            statements.append(f'''CREATE TRIGGER IF NOT EXISTS event_{table}_creation BEFORE INSERT ON EventLog
                WHEN NEW.{target} IS NOT NULL AND NEW.event_type='CREATED'
                AND (NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT (SELECT state FROM {quote(table)} WHERE id=NEW.{target}))
                BEGIN SELECT RAISE(ABORT,'creation state mismatch'); END;''')
    statements.append('''CREATE TRIGGER IF NOT EXISTS observation_has_no_state BEFORE INSERT ON EventLog
        WHEN NEW.event_type='OBSERVED' AND (NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT NULL)
        BEGIN SELECT RAISE(ABORT,'observation cannot change state'); END;''')
    statements.extend(_business_triggers())
    return "\n".join(statements)


def _guard(table, name, condition):
    return [f'''CREATE TRIGGER IF NOT EXISTS {name}_{operation} BEFORE {operation} ON {quote(table)}
        WHEN NOT ({condition}) BEGIN SELECT RAISE(ABORT,'{name}'); END;''' for operation in ("INSERT", "UPDATE")]


def _business_triggers():
    statements = []
    statements += _guard("ReturnLine", "return_line_same_order", """EXISTS(
        SELECT 1 FROM ReturnRequest r JOIN OrderLine o ON o.order_id=r.order_id
        WHERE r.id=NEW.request_id AND o.id=NEW.order_line_id)""")
    statements += _guard("AuthorizationLine", "authorization_same_request", """EXISTS(
        SELECT 1 FROM ReturnAuthorization a JOIN ReturnLine l ON l.request_id=a.request_id
        WHERE a.id=NEW.authorization_id AND l.id=NEW.return_line_id AND NEW.approved_quantity<=l.requested_quantity)""")
    statements += _guard("ShipmentLine", "shipment_quantity_limit", """EXISTS(
        SELECT 1 FROM AuthorizationLine a WHERE a.id=NEW.authorization_line_id
        AND NEW.shipped_quantity+COALESCE((SELECT SUM(shipped_quantity) FROM ShipmentLine
        WHERE authorization_line_id=a.id AND id<>NEW.id),0)<=a.approved_quantity)""")
    statements += _guard("Inspection", "inspection_received_limit", """EXISTS(
        SELECT 1 FROM ShipmentLine l JOIN ReturnShipment s ON s.id=l.shipment_id
        WHERE l.id=NEW.shipment_line_id AND s.delivered_at IS NOT NULL AND NEW.inspected_at>=s.delivered_at
        AND NEW.inspected_quantity+COALESCE((SELECT SUM(inspected_quantity) FROM Inspection
        WHERE shipment_line_id=l.id AND id<>NEW.id),0)<=l.received_quantity)""")
    inspection_link = """EXISTS(SELECT 1 FROM Inspection i JOIN ShipmentLine s ON s.id=i.shipment_line_id
        JOIN AuthorizationLine a ON a.id=s.authorization_line_id
        WHERE i.id=NEW.inspection_id AND a.return_line_id=NEW.return_line_id)"""
    for table in ("RefundObligation", "InventoryDisposition"):
        statements += _guard(table, table+"_inspection_link", "NEW.inspection_id IS NULL OR " + inspection_link)
    statements += _guard("Refund", "refund_success_guard", """NEW.state<>'SUCCEEDED' OR EXISTS(
        SELECT 1 FROM RefundObligation o JOIN Inspection i ON i.id=o.inspection_id
        JOIN ReturnLine l ON l.id=o.return_line_id JOIN OrderLine ol ON ol.id=l.order_line_id
        WHERE o.id=NEW.obligation_id AND i.state='FINALIZED' AND NEW.attempted_at>=i.inspected_at
        AND NEW.paid_minor+COALESCE((SELECT SUM(paid_minor) FROM Refund WHERE obligation_id=o.id AND id<>NEW.id),0)<=o.entitlement_minor
        AND NEW.paid_minor+COALESCE((SELECT SUM(r.paid_minor) FROM Refund r JOIN RefundObligation b ON b.id=r.obligation_id
        JOIN ReturnLine rl ON rl.id=b.return_line_id WHERE rl.order_line_id=ol.id AND r.id<>NEW.id),0)<=ol.paid_minor)""")
    statements += _guard("InventoryDisposition", "accepted_disposition_guard", """NEW.state<>'ACCEPTED' OR EXISTS(
        SELECT 1 FROM Inspection i WHERE i.id=NEW.inspection_id AND i.state='FINALIZED'
        AND NEW.decided_at>=i.inspected_at AND (NEW.action<>'RESTOCK' OR i.condition='SELLABLE')
        AND NEW.quantity+COALESCE((SELECT SUM(quantity) FROM InventoryDisposition WHERE inspection_id=i.id
        AND state='ACCEPTED' AND id<>NEW.id),0)<=i.inspected_quantity)""")
    statements += _guard("InventoryMovement", "movement_requires_accepted_decision", """EXISTS(
        SELECT 1 FROM InventoryDisposition d WHERE d.id=NEW.disposition_id AND d.state='ACCEPTED'
        AND NEW.quantity=d.quantity AND NEW.moved_at>=d.decided_at)""")
    # Evidence used by posted transactions cannot be edited afterwards.
    for table in ("Refund", "InventoryDisposition", "Inspection"):
        terminal = {"Refund": "OLD.state IN ('SUCCEEDED','FAILED','REJECTED')", "InventoryDisposition": "OLD.state IN ('ACCEPTED','REJECTED')", "Inspection": "OLD.state='FINALIZED'"}[table]
        statements.append(f'''CREATE TRIGGER IF NOT EXISTS {table}_terminal_immutable BEFORE UPDATE ON {table}
            WHEN {terminal} BEGIN SELECT RAISE(ABORT,'terminal evidence is immutable'); END;''')
        statements.append(f'''CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table}
            BEGIN SELECT RAISE(ABORT,'audit evidence cannot be deleted'); END;''')
    statements.append('''CREATE TRIGGER IF NOT EXISTS obligation_fixed_after_attempt BEFORE UPDATE ON RefundObligation
        WHEN EXISTS(SELECT 1 FROM Refund WHERE obligation_id=OLD.id)
        BEGIN SELECT RAISE(ABORT,'attempted obligation is immutable'); END;''')
    # Freeze financial facts/quantity evidence once downstream records depend on them.
    frozen = {
        "OrderLine": "EXISTS(SELECT 1 FROM ReturnLine WHERE order_line_id=OLD.id)",
        "ShipmentLine": "EXISTS(SELECT 1 FROM Inspection WHERE shipment_line_id=OLD.id)",
        "AuthorizationLine": "EXISTS(SELECT 1 FROM ShipmentLine WHERE authorization_line_id=OLD.id)",
        "ReturnPolicy": "EXISTS(SELECT 1 FROM ReturnRequest WHERE policy_id=OLD.id)",
    }
    for table, used in frozen.items():
        statements.append(f'''CREATE TRIGGER IF NOT EXISTS {table}_freeze_referenced_evidence BEFORE UPDATE ON {quote(table)}
            WHEN {used} BEGIN SELECT RAISE(ABORT,'referenced evidence is immutable'); END;''')
    return statements


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    """Every application connection enables and verifies foreign-key enforcement."""
    conn = sqlite3.connect(str(path), isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        conn.close()
        raise RuntimeError("Foreign-key enforcement unavailable")
    return conn


@contextmanager
def transaction(conn):
    """Atomic writer; nested operations use savepoints, without committing caller work."""
    nested = conn.in_transaction
    if nested:
        conn.execute("SAVEPOINT returns_operation")
    else:
        conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        if nested:
            conn.execute("ROLLBACK TO returns_operation")
            conn.execute("RELEASE returns_operation")
        else:
            conn.rollback()
        raise
    else:
        if nested:
            conn.execute("RELEASE returns_operation")
        else:
            conn.commit()


def initialize(conn):
    if conn.in_transaction:
        raise RuntimeError("Initialize before beginning business transactions")
    version_exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name='SchemaVersion'").fetchone()
    if version_exists and [r[0] for r in conn.execute("SELECT version FROM SchemaVersion")] != [2]:
        raise RuntimeError("Unsupported schema version; explicit migration required")
    try:
        conn.executescript("BEGIN IMMEDIATE;\n" + schema_sql() + "\nINSERT OR IGNORE INTO SchemaVersion VALUES(2);\nCOMMIT;")
    except BaseException:
        conn.rollback()
        raise
