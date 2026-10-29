"""Private staging, measured validation/export, then promotion of complete output."""

from pathlib import Path
from copy import deepcopy
import json
import hashlib
import platform
import shutil
import sqlite3
import tempfile
import time
from contextlib import contextmanager

from .config import DEFAULT, canonical_json, validate_config
from .exports import export_artifacts, checksum
from .generator import BaselineGenerator
from .schema import connect, initialize, quote
from .validation import validate


@contextmanager
def staging(destination):
    destination=Path(destination).resolve()
    if destination.exists(): raise FileExistsError(f"Output already exists; choose a new directory: {destination}")
    destination.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix="."+destination.name+".staging-",dir=destination.parent))
    try:
        yield stage
        if destination.exists(): raise FileExistsError(f"Output appeared during generation: {destination}")
        stage.rename(destination)
    finally:
        if stage.exists():
            if stage.resolve().parent!=destination.parent or not stage.name.startswith("."+destination.name+".staging-"):
                raise RuntimeError("Refusing cleanup outside the owned staging directory")
            shutil.rmtree(stage)


def generate(destination, config, *, command=None, progress=None):
    validate_config(config)
    source_fingerprint=generator_source_fingerprint()
    started=time.perf_counter()
    with staging(destination) as stage:
        conn=connect(stage/"returns.db")
        try:
            initialize(conn)
            before=time.perf_counter()
            sidecars=BaselineGenerator(conn,config).run(progress)
            generation_seconds=time.perf_counter()-before
            if progress: progress("validating persisted baseline")
            before=time.perf_counter()
            result=validate(conn,config)
            validation_seconds=time.perf_counter()-before
            if result["status"]!="PASS":
                failures=[m for m in result["metrics"] if m["status"]=="FAIL"]
                raise ValueError("Baseline validation failed: "+json.dumps(failures))
            if progress: progress("writing canonical CSV, JSON and SQL snapshots")
            before=time.perf_counter()
            manifest=export_artifacts(conn,stage,config,result,sidecars,generator_source_sha256=source_fingerprint)
            export_seconds=time.perf_counter()-before
        finally: conn.close()
        metadata={"command":command or [],"python":platform.python_version(),"sqlite":sqlite3.sqlite_version,
            "generation_seconds":generation_seconds,"validation_seconds":validation_seconds,"export_seconds":export_seconds,
            "total_seconds":time.perf_counter()-started,
            "output_sizes_bytes":{p.relative_to(stage).as_posix():p.stat().st_size for p in sorted(stage.rglob('*')) if p.is_file()}}
        (stage/"run_metadata.json").write_text(canonical_json(metadata),encoding="utf-8",newline="\n")
    return {"output":str(Path(destination).resolve()),"manifest":manifest,"runtime":metadata}


LEGACY_V1_GENERATION_FIELDS = ("coverage_strata", "order_line_weights", "return_reason_weights",
    "ordinary_condition_weights", "damage_condition_weights")


def validation_snapshot_config(config):
    """Fill only missing generation-distribution fields for older v1 validation.

    These fields are not used to recompute policy, financial or lifecycle facts.
    The caller's original snapshot and its manifest checksum remain unchanged.
    This is not evidence that the old generator is available for reproduction.
    """
    snapshot=deepcopy(config)
    missing=[name for name in LEGACY_V1_GENERATION_FIELDS if name not in snapshot]
    if snapshot.get("config_version")==1:
        for name in missing: snapshot[name]=deepcopy(DEFAULT[name])
    validate_config(snapshot)
    return snapshot, missing


def generator_source_fingerprint():
    """Fingerprint package source bytes in stable name order for provenance."""
    digest=hashlib.sha256()
    for path in sorted(Path(__file__).resolve().parent.glob("*.py"),key=lambda p:p.name):
        digest.update(path.name.encode("utf-8")); digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def validate_dataset(directory):
    directory=Path(directory)
    config, missing=validation_snapshot_config(json.loads((directory/"configuration.json").read_text(encoding="utf-8")))
    if not (directory/"returns.db").is_file(): raise FileNotFoundError("Dataset database not found")
    conn=connect(directory/"returns.db")
    try:
        result=validate(conn,config)
        if missing:
            result["configuration_compatibility"]={"version":1,"validation_only_defaults":missing,
                "snapshot_modified":False,"regeneration_of_historical_output_verified":False}
        return result
    finally: conn.close()


def reexport(source, destination):
    source=Path(source)
    config, missing=validation_snapshot_config(json.loads((source/"configuration.json").read_text(encoding="utf-8")))
    if missing:
        raise ValueError("Earlier version-1 snapshot lacks generator settings; validation is supported but re-export is disabled to avoid misrepresenting its provenance")
    if not (source/"returns.db").is_file(): raise FileNotFoundError("Dataset database not found")
    old_manifest_path=source/"manifest.json"
    old_manifest=json.loads(old_manifest_path.read_text(encoding="utf-8")) if old_manifest_path.is_file() else {}
    original_fingerprint=old_manifest.get("generator_source_sha256")
    started=time.perf_counter()
    with staging(destination) as stage:
        original=connect(source/"returns.db"); conn=connect(stage/"returns.db")
        try: original.backup(conn)
        finally: original.close()
        try:
            result=validate(conn,config)
            if result["status"]!="PASS": raise ValueError("Cannot export an invalid baseline")
            sidecars={"catalog":json.loads((source/"catalog.json").read_text(encoding="utf-8")),
                "customers":json.loads((source/"customer_profiles.json").read_text(encoding="utf-8"))}
            manifest=export_artifacts(conn,stage,config,result,sidecars,generator_source_sha256=original_fingerprint)
        finally: conn.close()
        (stage/"run_metadata.json").write_text(canonical_json({"command":"export","source":str(source.resolve()),"total_seconds":time.perf_counter()-started}),encoding="utf-8",newline="\n")
    return {"output":str(Path(destination).resolve()),"manifest":manifest}


def compare_datasets(left, right):
    """Rehash actual files and inspect DB counts; do not trust stored hashes alone."""
    manifests=[]; actual_hashes=[]; bad=[]; db_counts=[]
    for label,directory in (("left",Path(left)),("right",Path(right))):
        manifest=json.loads((directory/"manifest.json").read_text(encoding="utf-8"))
        hashes={}
        expected={f["name"] for f in manifest["files"]}|set(manifest["checksum_exclusions"])
        actual={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
        if expected!=actual: bad.append([label,"artifact_set",sorted(expected^actual)])
        for entry in manifest["files"]:
            path=directory/entry["name"]
            if not path.resolve().is_relative_to(directory.resolve()): raise ValueError("Manifest file escapes dataset directory")
            if not path.is_file(): bad.append([label,entry["name"],"missing"]); continue
            digest=checksum(path); hashes[entry["name"]]=digest
            if digest!=entry["sha256"]: bad.append([label,entry["name"],"stored checksum mismatch"])
        if not (directory/"returns.db").is_file(): raise FileNotFoundError("Dataset database missing")
        conn=connect(directory/"returns.db")
        try:
            counts={name:conn.execute(f'SELECT count(*) FROM {quote(name)}').fetchone()[0] for name in manifest["actual_counts"]}
            for table in counts:
                ordering="entity" if table=="IdSequence" else ("version" if table=="SchemaVersion" else "id")
                digest=hashlib.sha256(); digest.update(b"["); first=True
                for row in conn.execute(f'SELECT * FROM {quote(table)} ORDER BY {quote(ordering)}'):
                    if not first: digest.update(b",")
                    digest.update(json.dumps(dict(row),sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")); first=False
                digest.update(b"]\n")
                if digest.hexdigest()!=hashes.get("json/"+table+".json"): bad.append([label,table,"DB logical content differs from JSON export"])
        finally: conn.close()
        if counts!=manifest["actual_counts"]: bad.append([label,"database row counts","mismatch"])
        manifests.append(manifest); actual_hashes.append(hashes); db_counts.append(counts)
    unequal=sorted(name for name in set(actual_hashes[0])|set(actual_hashes[1]) if actual_hashes[0].get(name)!=actual_hashes[1].get(name))
    equal_count=sum(actual_hashes[0].get(name)==actual_hashes[1].get(name) for name in set(actual_hashes[0])|set(actual_hashes[1]))
    same_counts=db_counts[0]==db_counts[1]
    same_config=manifests[0]["configuration_sha256"]==manifests[1]["configuration_sha256"]
    source_hashes=[m.get("generator_source_sha256") for m in manifests]
    source_identity=("UNAVAILABLE" if any(value is None for value in source_hashes) else
        "MATCH" if source_hashes[0]==source_hashes[1] else "DIFFERENT")
    return {"status":"PASS" if not bad and not unequal and same_counts and same_config else "FAIL",
        "matching_hashes_numerator":equal_count,"compared_files_denominator":len(set(actual_hashes[0])|set(actual_hashes[1])),
        "interpretation":"Identical rehashed deterministic artifacts / compared deterministic artifacts; database bytes, manifest self-hash and volatile metadata excluded",
        "row_counts_equal":same_counts,"configuration_equal":same_config,"generator_source_identity":source_identity,
        "generator_source_sha256":source_hashes,"row_counts":db_counts,
        "unequal_files":unequal,"integrity_errors":bad,"left":str(Path(left).resolve()),"right":str(Path(right).resolve()),
        "hashes":actual_hashes}
