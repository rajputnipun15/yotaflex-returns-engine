"""Atomic state projection + append-only event history, without volatile clocks."""

from datetime import datetime, timezone

from .ids import allocate_id
from .model import TABLES, TARGETS, TRANSITIONS
from .schema import transaction, quote


def validate_timestamp(value):
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError("Use canonical YYYY-MM-DDTHH:MM:SSZ UTC timestamps")


def record_event(conn, entity, entity_id, *, event_type, occurred_at, reason_code,
                 correlation_id, new_state=None, attempt_id=None, changes=None):
    """Append event and change the matching state projection in one transaction.

    Lifecycle business prerequisites (window, aggregate progress, reservation)
    are the later workflow's responsibility. This checks the transition allowlist.
    """
    if entity not in TARGETS:
        raise ValueError("Unknown event target")
    validate_timestamp(occurred_at)
    changes = dict(changes or {})
    mutable = {f.name for f in TABLES[entity] if f.name not in ("id", "state") and not f.ref}
    if set(changes) - mutable:
        raise ValueError("Cannot mutate identifiers, links or unknown fields")
    if event_type != "STATE_CHANGED" and (new_state is not None or changes):
        raise ValueError("Only state changes can update projections")
    with transaction(conn):
        row = conn.execute(f'SELECT * FROM {quote(entity)} WHERE id=?', (entity_id,)).fetchone()
        if row is None:
            raise ValueError("Event target does not exist")
        previous = row["state"] if "state" in row.keys() else None
        if event_type == "STATE_CHANGED":
            if new_state not in TRANSITIONS.get(entity, {}).get(previous, ()):
                raise ValueError("Forbidden lifecycle transition")
        event_id = allocate_id(conn, "EventLog")
        conn.execute(f'''INSERT INTO EventLog
            (id,{quote(entity+'_id')},attempt_id,event_type,previous_state,new_state,occurred_at,reason_code,correlation_id)
            VALUES(?,?,?,?,?,?,?,?,?)''', (event_id, entity_id, attempt_id, event_type,
                previous if event_type == "STATE_CHANGED" else None,
                previous if event_type == "CREATED" else new_state, occurred_at, reason_code, correlation_id))
        if event_type == "STATE_CHANGED":
            changes["state"] = new_state
            assignments = ",".join(f'{quote(k)}=?' for k in changes)
            conn.execute(f'UPDATE {quote(entity)} SET {assignments} WHERE id=?', (*changes.values(), entity_id))
        return event_id
