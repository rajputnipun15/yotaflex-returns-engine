"""Local schema, baseline generation, validation, export and comparison CLI."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from .schema import connect, initialize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    for name in ("init-db","inspect-db"):
        command=commands.add_parser(name)
        command.add_argument("--database",required=True)
    command=commands.add_parser("generate")
    command.add_argument("--scale",choices=("starter","full","custom"),default="starter")
    command.add_argument("--seed",type=int)
    command.add_argument("--config")
    command.add_argument("--orders",type=int)
    command.add_argument("--requests",type=int)
    command.add_argument("--return-lines",type=int)
    command.add_argument("--output",required=True)
    for name in ("validate","export"):
        command=commands.add_parser(name); command.add_argument("--input",required=True)
        if name=="export": command.add_argument("--output",required=True)
    command=commands.add_parser("reproduce")
    command.add_argument("--left",required=True); command.add_argument("--right",required=True)
    command.add_argument("--report")
    args = parser.parse_args()
    if args.command in ("generate","validate","export","reproduce"):
        from .config import resolve_config
        from .pipeline import generate, validate_dataset, reexport, compare_datasets
        try:
            if args.command=="generate":
                config=resolve_config(scale=args.scale,seed=args.seed,path=args.config,
                    counts={"orders":args.orders,"requests":args.requests,"return_lines":args.return_lines})
                result=generate(args.output,config,command=sys.argv,progress=lambda text:print(text,file=sys.stderr,flush=True))
                output={"output":result["output"],"status":result["manifest"]["validation_status"],"row_counts":result["manifest"]["actual_counts"],
                    "runtime_seconds":result["runtime"]["total_seconds"],"manifest":"manifest.json"}
            elif args.command=="validate":
                result=validate_dataset(args.input)
                output={k:v for k,v in result.items() if k not in ("quantity_summary","order_totals")}
            elif args.command=="export":
                result=reexport(args.input,args.output)
                output={"output":result["output"],"status":result["manifest"]["validation_status"]}
            else:
                output=compare_datasets(args.left,args.right)
                if args.report:
                    with Path(args.report).open("x",encoding="utf-8",newline="\n") as report: json.dump(output,report,indent=2)
            print(json.dumps(output,indent=2))
            return 0 if output.get("status")=="PASS" else 1
        except (ValueError,OSError,sqlite3.Error,KeyError,TypeError) as exc:
            parser.exit(2,f"returns_engine: {exc}\n")
    if args.command == "inspect-db" and not Path(args.database).is_file():
        parser.error("Database does not exist")
    conn = connect(args.database)
    try:
        if args.command == "init-db":
            initialize(conn)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        print(json.dumps({"database": args.database, "foreign_keys": conn.execute("PRAGMA foreign_keys").fetchone()[0],
            "tables": tables, "foreign_key_violations": [list(r) for r in conn.execute("PRAGMA foreign_key_check")],
            "row_counts":{table:conn.execute('SELECT count(*) FROM "'+table.replace('"','""')+'"').fetchone()[0] for table in tables},
            "integrity_check": conn.execute("PRAGMA integrity_check").fetchone()[0]}, indent=2))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
