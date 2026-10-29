"""Canonical streaming exports, checksum manifests and safe snapshot SQL."""

import csv
import hashlib
import json
from pathlib import Path

from .config import canonical_json
from .generator import GENERATOR_VERSION
from .model import TABLES
from .schema import schema_sql, quote

EXPORT_TABLES=("SchemaVersion","IdSequence",*TABLES)


def checksum(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()


def sql_value(value):
    if value is None: return "NULL"
    if type(value) is int: return str(value)
    if not isinstance(value,str): raise TypeError("Only INTEGER/TEXT/NULL are exported")
    return "'"+value.replace("'","''")+"'"


def export_artifacts(conn, directory, config, validation, sidecars, *, generator_source_sha256=None):
    """Destination must be a private staging directory owned by the caller."""
    directory=Path(directory)
    files=[]
    def register(relative, rows=None):
        path=directory/relative
        files.append({"name":relative,"row_count":rows,"sha256":checksum(path),"size_bytes":path.stat().st_size})
    def write_json(relative,value,rows=None):
        (directory/relative).write_text(canonical_json(value),encoding="utf-8",newline="\n")
        register(relative,rows)
    for folder in ("csv","json"): (directory/folder).mkdir()
    for table in EXPORT_TABLES:
        columns=[r[1] for r in conn.execute(f'PRAGMA table_info({quote(table)})')]
        order="entity" if table=="IdSequence" else ("version" if table=="SchemaVersion" else "id")
        count=0
        with (directory/"csv"/(table+".csv")).open("w",encoding="utf-8",newline="") as csv_file, (directory/"json"/(table+".json")).open("w",encoding="utf-8",newline="\n") as json_file:
            writer=csv.writer(csv_file,lineterminator="\n")
            writer.writerow(columns); json_file.write("[")
            for row in conn.execute(f'SELECT * FROM {quote(table)} ORDER BY {quote(order)}'):
                if any(value == "\\N" for value in row if value is not None):
                    raise ValueError(f"{table} contains the reserved CSV NULL sentinel as literal data")
                writer.writerow(["\\N" if value is None else value for value in row])
                if count: json_file.write(",")
                json_file.write(json.dumps(dict(row),sort_keys=True,ensure_ascii=False,separators=(",",":")))
                count+=1
            json_file.write("]\n")
        register("csv/"+table+".csv",count); register("json/"+table+".json",count)
    (directory/"schema.sql").write_text("PRAGMA foreign_keys=ON;\n"+schema_sql()+"\n",encoding="utf-8",newline="\n")
    register("schema.sql")
    triggers=list(conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' ORDER BY name"))
    with (directory/"seed.sql").open("w",encoding="utf-8",newline="\n") as stream:
        stream.write("-- Trusted snapshot import: empty target only; all triggers restored atomically.\nPRAGMA foreign_keys=ON;\nBEGIN IMMEDIATE;\n")
        stream.write(schema_sql()+"\n")
        guard=" OR ".join(f'EXISTS(SELECT 1 FROM {quote(t)})' for t in (*TABLES,"IdSequence"))
        stream.write('CREATE TEMP TABLE _ReturnsSeedGuard(ok INTEGER CHECK(ok=1));\n')
        stream.write("INSERT INTO _ReturnsSeedGuard VALUES(CASE WHEN "+guard+" THEN 0 ELSE 1 END);\n")
        # Final snapshots contain historical events whose previous state is not
        # the final projection. Suspend ONLY triggers within this empty restore,
        # retain STRICT/CHECK/PK/FK/unique indexes, restore every trigger before commit.
        for trigger in triggers: stream.write("DROP TRIGGER "+quote(trigger["name"])+";\n")
        for table in EXPORT_TABLES:
            order="entity" if table=="IdSequence" else ("version" if table=="SchemaVersion" else "id")
            for row in conn.execute(f'SELECT * FROM {quote(table)} ORDER BY {quote(order)}'):
                verb="INSERT OR IGNORE" if table=="SchemaVersion" else "INSERT"
                stream.write(verb+" INTO "+quote(table)+" VALUES("+",".join(sql_value(value) for value in row)+");\n")
        for trigger in triggers: stream.write(trigger["sql"]+";\n")
        stream.write("DROP TABLE _ReturnsSeedGuard;\nCOMMIT;\n")
    register("seed.sql",sum(validation["row_counts"].values()))
    write_json("configuration.json",config)
    write_json("catalog.json",sidecars["catalog"],len(sidecars["catalog"]))
    write_json("customer_profiles.json",sidecars["customers"],len(sidecars["customers"]))
    write_json("quantity_summary.json",validation["quantity_summary"],len(validation["quantity_summary"]))
    write_json("order_totals.json",validation["order_totals"],len(validation["order_totals"]))
    report={k:v for k,v in validation.items() if k not in ("quantity_summary","order_totals")}
    write_json("validation.json",report)
    lines=["# Measured baseline validation", "", "Status: "+report["status"],"",report["scope"], ""]
    for metric in report["metrics"]:
        lines.append(f"- {metric['check_id']}: {metric['numerator']}/{metric['denominator']} violations; {metric['status']}. {metric['interpretation']}.")
    (directory/"validation.md").write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")
    register("validation.md")
    config_hash=hashlib.sha256(canonical_json(config).encode("utf-8")).hexdigest()
    write_json("source_manifest.json",{"source_type":"fully synthetic","external_sources":[],
        "generator_version":GENERATOR_VERSION,"configuration_sha256":config_hash,
        "license_note":"No external dataset imported. Synthetic policy assumptions, not measured industry statistics."})
    manifest={"manifest_version":1,"master_seed":config["seed"],"scale":config["scale"],"configuration_sha256":config_hash,
        "schema_version":conn.execute("SELECT version FROM SchemaVersion").fetchone()[0],"generator_version":GENERATOR_VERSION,
        "generator_source_sha256":generator_source_sha256,
        "requested_counts":config["counts"],"actual_counts":validation["row_counts"],"validation_status":validation["status"],
        "generation_command":["python","-m","returns_engine","generate","--scale",config["scale"],"--seed",str(config["seed"]),
            "--config","configuration.json","--orders",str(config["counts"]["orders"]),"--requests",str(config["counts"]["requests"]),
            "--return-lines",str(config["counts"]["return_lines"]),"--output","<OUTPUT>"],
        "files":sorted(files,key=lambda f:f["name"]),
        "checksum_exclusions":{"manifest.json":"Self-referential hash excluded","returns.db":"SQLite physical bytes are not a canonical serialization",
            "run_metadata.json":"Measured runtime, command paths and environment are volatile"}}
    (directory/"manifest.json").write_text(canonical_json(manifest),encoding="utf-8",newline="\n")
    return manifest
