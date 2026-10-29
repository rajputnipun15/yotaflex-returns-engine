"""Render reviewable dictionary entries from the actual DDL field metadata."""

from .model import TABLES, CONSTRAINTS


def render_dictionary():
    lines = ["# Data dictionary (implemented Phase 2 schema)", "",
        "Generated from returns_engine.model; checked against PRAGMA table_info in tests. Phase 3 baseline generation uses the unchanged Phase 2 schema.", "",
        "All tables are STRICT. All identifiers are NOT NULL primary keys, immutable, case-sensitive and unique per table. All FKs use RESTRICT on update/delete and are indexed. No field has an implicit business default; supply all required values explicitly. Optional means SQL NULL is allowed.", "",
        "Money is integer minor currency units; currency is inherited from the original Order. UTC timestamps use YYYY-MM-DDTHH:MM:SSZ. SQL checks lexical form; the event utility also validates calendar dates. See schema.md for relationships/transitions and business_rules.md for rules and enforcement boundaries.", "",
        "Sensitivity: all business data must be invented, public-safe synthetic data. Names, reason/override text and JSON payloads must never contain real personal information, secrets or confidential material. Technical correlation IDs and IDs are public-safe only when synthetic.", ""]
    for table, fields in TABLES.items():
        lines.extend(["## " + table, ""])
        for field in fields:
            key = "PK" if field.name == "id" else ("FK -> " + field.ref + ".id" if field.ref else "neither")
            unique = "Unique primary key" if field.name == "id" else "No standalone uniqueness unless specified in table constraints below"
            allowed = ", ".join(field.values) or ("Integer" if field.sql_type == "INTEGER" else "Nonblank text when non-null")
            lines.extend([f"### {table}.{field.name}",
                f"- Type: {field.sql_type}; {'required (NOT NULL)' if field.required else 'optional (nullable)' }.",
                f"- Allowed values: {allowed}. Unit: {field.unit}.",
                f"- Key: {key}. Uniqueness: {unique}.",
                f"- Default: {field.default if field.default is not None else 'none'}.",
                f"- Validation: {field.check or 'STRICT storage type; enum and referential constraints where specified'}.",
                f"- Meaning: {field.meaning}",
                "- Public export: synthetic values only; free text/JSON requires sensitivity review.", ""])
        lines.extend(["Table constraints (in addition to field/FK/trigger rules):", ""])
        lines.extend("- " + rule for rule in CONSTRAINTS.get(table, ["Primary key and field constraints; see schema.md for triggers."]))
        if table == "Refund": lines.append("- UNIQUE(payment_key) WHERE state='SUCCEEDED'; failed/blocked retries may repeat the key.")
        lines.append("")
    lines.extend(["## Internal bookkeeping", "",
        "SchemaVersion.version: required INTEGER PK, exactly 2; technical migration marker, not business data.",
        "IdSequence.entity: required TEXT PK, allocator entity name; IdSequence.last_value: required INTEGER 1..999999, last reserved counter. No default. Writer transaction required. These are technical tables, not assessment entities.", "",
        "## Phase 3 export extensions", "",
        "CSV/JSON table exports use exactly the fields above (including technical table fields). CSV column order follows DDL; JSON fields retain their names, use native integers/nulls and canonical sorted keys. CSV NULL is the literal backslash-N sentinel. No floats or ground-truth labels are added.", "",
        "Sidecar and calculated export fields are NOT database columns. Their types, references, units and derivations are separately documented in export_contract.md: catalog.json, customer_profiles.json, quantity_summary.json, order_totals.json, configuration.json, manifest.json, validation.json and source_manifest.json. No schema migration was needed.", ""])
    return "\n".join(lines)
