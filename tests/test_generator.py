import csv
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from returns_engine.config import resolve_config, validate_config, canonical_json
from returns_engine.exports import checksum
from returns_engine.generator import BaselineGenerator
from returns_engine.money import allocate_proportional, basis_points
from returns_engine.pipeline import generate, compare_datasets, validate_dataset, reexport, generator_source_fingerprint
from returns_engine.policy import authorize_request, cancel_authorization, evaluate_line, reserved_quantity
from returns_engine.schema import connect, initialize


def tiny(seed=20261022):
    return resolve_config(scale="custom",seed=seed,counts={"orders":20,"requests":14,"return_lines":22})


def approval_fixture(conn):
    conn.executescript('''
    INSERT INTO Customer VALUES('CUS-2026-000001','Synthetic','ACTIVE','2026-01-01T00:00:00Z');
    INSERT INTO Product VALUES('PRD-2026-000001','CLOTHING','Synthetic shirt');
    INSERT INTO ReturnPolicy VALUES('POL-2026-000001',30,'[]',0,'2026-01-01T00:00:00Z',NULL);
    INSERT INTO "Order" VALUES('ORD-2026-000001','CUS-2026-000001','INR','2026-08-30T00:00:00Z','2026-09-01T00:00:00Z',0,'DELIVERED');
    INSERT INTO OrderLine VALUES('ORL-2026-000001','ORD-2026-000001','PRD-2026-000001',3,100,0,0,0,300);
    INSERT INTO ReturnRequest VALUES('RMA-2026-000001','ORD-2026-000001','POL-2026-000001','2026-09-02T00:00:00Z','REFUND',NULL,'REQUESTED');
    INSERT INTO ReturnLine VALUES('RMAL-RMA-2026-000001-01','RMA-2026-000001','ORL-2026-000001',1,2,'SIZE','REQUESTED');
    INSERT INTO ReturnRequest VALUES('RMA-2026-000002','ORD-2026-000001','POL-2026-000001','2026-09-03T00:00:00Z','REFUND',NULL,'REQUESTED');
    INSERT INTO ReturnLine VALUES('RMAL-RMA-2026-000002-01','RMA-2026-000002','ORL-2026-000001',1,3,'SIZE','REQUESTED');
    ''')


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def bundle(self,name="dataset",seed=20261022,config=None):
        path=self.root/name
        generate(path,config or tiny(seed))
        return path

    def test_same_seed_all_canonical_files_equal(self):
        left=self.bundle("left"); right=self.bundle("right")
        report=compare_datasets(left,right)
        self.assertEqual(report["status"],"PASS",report)
        self.assertEqual(report["matching_hashes_numerator"],report["compared_files_denominator"])

    def test_different_seed_changes_data_preserves_all_checks(self):
        left=self.bundle("left"); right=self.bundle("right",seed=9)
        self.assertNotEqual(checksum(left/"json/OrderLine.json"),checksum(right/"json/OrderLine.json"))
        for dataset in (left,right): self.assertEqual(validate_dataset(dataset)["status"],"PASS")

    def test_equivalent_config_key_order_has_identical_content(self):
        config=tiny()
        normalized=json.loads(canonical_json(config))
        left=self.bundle("left",config=config); right=self.bundle("right",config=normalized)
        self.assertEqual(compare_datasets(left,right)["status"],"PASS")

    def test_full_counts_and_shared_pipeline_selection(self):
        full=resolve_config(scale="full")
        self.assertEqual(full["counts"],{"orders":30000,"requests":5000,"return_lines":8000})
        for scale in ("starter","full"):
            config=resolve_config(scale=scale)
            with patch.object(BaselineGenerator,"run",side_effect=RuntimeError("pipeline reached")) as run:
                with self.assertRaisesRegex(RuntimeError,"pipeline reached"): generate(self.root/scale,config)
                run.assert_called_once()
                self.assertFalse((self.root/scale).exists())

    def test_starter_and_custom_config_counts(self):
        self.assertEqual(resolve_config()["counts"],{"orders":300,"requests":50,"return_lines":80})
        dataset=self.bundle()
        counts=json.loads((dataset/"manifest.json").read_text())["actual_counts"]
        self.assertEqual([counts[t] for t in ("Order","ReturnRequest","ReturnLine")],[20,14,22])

    def test_fk_same_order_quantity_money_and_events(self):
        dataset=self.bundle()
        result=validate_dataset(dataset)
        for metric in result["metrics"]:
            self.assertEqual(metric["numerator"],0,metric)
        self.assertEqual(result["row_counts"]["ReturnLine"],22)
        for q in result["quantity_summary"]:
            self.assertLessEqual(q["authorized_quantity"],q["requested_quantity"])
            self.assertLessEqual(q["successfully_refunded_quantity"],q["inspected_quantity"])

    def test_partial_repeated_rejected_and_pending_coverage(self):
        dataset=self.bundle()
        result=validate_dataset(dataset)
        self.assertGreater(result["coverage"]["partially_authorized_lines"],0)
        self.assertGreater(result["coverage"]["partial_requested_lines"],0)
        for state in ("REQUESTED","REJECTED","APPROVED","RECEIVED","INSPECTED","CLOSED"):
            self.assertGreater(result["coverage"]["request_states"].get(state,0),0,state)

    def test_missing_shipments_have_no_receipt_inspection_or_payment(self):
        dataset=self.bundle()
        conn=connect(dataset/"returns.db")
        try:
            self.assertGreater(conn.execute("SELECT count(*) FROM ReturnShipment WHERE state='MISSING'").fetchone()[0],0)
            self.assertEqual(conn.execute('''SELECT count(*) FROM ShipmentLine l JOIN ReturnShipment s ON s.id=l.shipment_id
                WHERE s.state='MISSING' AND (l.received_quantity<>0 OR EXISTS(SELECT 1 FROM Inspection i WHERE i.shipment_line_id=l.id))''').fetchone()[0],0)
        finally: conn.close()

    def test_rejected_pending_and_exchanges_have_no_unauthorized_cash(self):
        dataset=self.bundle()
        conn=connect(dataset/"returns.db")
        try:
            count=conn.execute('''SELECT count(*) FROM Refund f JOIN RefundObligation b ON b.id=f.obligation_id
                JOIN ReturnLine l ON l.id=b.return_line_id JOIN ReturnRequest r ON r.id=l.request_id
                WHERE r.state IN ('REQUESTED','REJECTED') OR r.resolution='EXCHANGE' ''').fetchone()[0]
            self.assertEqual(count,0)
            self.assertGreater(conn.execute("SELECT count(*) FROM ReturnRequest WHERE resolution='EXCHANGE' AND state<>'CLOSED'").fetchone()[0],0)
        finally: conn.close()

    def test_csv_json_database_parity_and_nulls(self):
        dataset=self.bundle(); conn=connect(dataset/"returns.db")
        try:
            for table in json.loads((dataset/"manifest.json").read_text())["actual_counts"]:
                order="entity" if table=="IdSequence" else ("version" if table=="SchemaVersion" else "id")
                actual=[dict(r) for r in conn.execute(f'SELECT * FROM "{table}" ORDER BY "{order}"')]
                self.assertEqual(json.loads((dataset/"json"/(table+".json")).read_text()),actual)
                with (dataset/"csv"/(table+".csv")).open(newline="",encoding="utf-8") as stream:
                    csv_rows=list(csv.DictReader(stream))
                expected=[{k:"\\N" if v is None else str(v) for k,v in r.items()} for r in actual]
                self.assertEqual(csv_rows,expected)
        finally: conn.close()

    def test_executable_sql_snapshot_restores_history_guards_and_values(self):
        dataset=self.bundle()
        conn=connect(self.root/"restored.db")
        try:
            conn.executescript((dataset/"seed.sql").read_text(encoding="utf-8"))
            self.assertEqual(validate(conn,tiny())["status"],"PASS")
            for table,count in json.loads((dataset/"manifest.json").read_text())["actual_counts"].items():
                self.assertEqual(conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0],count)
            with self.assertRaises(sqlite3.IntegrityError): conn.execute("DELETE FROM EventLog")
            with self.assertRaises(sqlite3.IntegrityError): conn.executescript((dataset/"seed.sql").read_text(encoding="utf-8"))
            conn.rollback()
        finally: conn.close()

    def test_existing_output_is_preserved(self):
        existing=self.root/"existing"; existing.mkdir(); (existing/"keep.txt").write_text("keep")
        with self.assertRaises(FileExistsError): generate(existing,tiny())
        self.assertEqual((existing/"keep.txt").read_text(),"keep")

    def test_generation_failure_has_no_successful_partial_dataset(self):
        with patch("returns_engine.pipeline.export_artifacts",side_effect=RuntimeError("injected IO failure")):
            with self.assertRaisesRegex(RuntimeError,"injected IO failure"): generate(self.root/"failed",tiny())
        self.assertFalse((self.root/"failed").exists())
        self.assertEqual(list(self.root.glob(".failed.staging-*")),[])

    def test_invalid_configuration_fails_before_any_output(self):
        for counts in ({"orders":1,"requests":5,"return_lines":4},{"orders":1,"requests":1,"return_lines":100}):
            with self.assertRaises(ValueError): resolve_config(scale="custom",counts=counts)
        with self.assertRaises(ValueError): resolve_config(scale="full",counts={"orders":1})
        with self.assertRaises(ValueError): resolve_config(scale="unknown")
        config=tiny(); config["fee_bps"]=1.5
        with self.assertRaises(ValueError): generate(self.root/"bad",config)
        self.assertFalse((self.root/"bad").exists())

    def test_reserved_null_marker_cannot_be_silently_exported(self):
        config=tiny(); category=config["categories"].pop("CLOTHING")
        config["categories"]["\\N"]=category
        with self.assertRaises(ValueError): validate_config(config)
        config=tiny(); config["return_reason_weights"]={"\\N":1}
        with self.assertRaises(ValueError): validate_config(config)
        dataset=self.bundle(); conn=connect(dataset/"returns.db")
        try: conn.execute("UPDATE Product SET description=? WHERE id=(SELECT min(id) FROM Product)",("\\N",))
        finally: conn.close()
        with self.assertRaisesRegex(ValueError,"reserved CSV NULL sentinel"):
            reexport(dataset,self.root/"invalid_export")
        self.assertFalse((self.root/"invalid_export").exists())

    def test_nonzero_tax_fee_and_discount_allocation(self):
        config=tiny(); config["tax_bps"]=1800; config["fee_bps"]=250
        dataset=self.bundle(config=config)
        result=validate_dataset(dataset)
        self.assertEqual(result["status"],"PASS",result["metrics"])
        conn=connect(dataset/"returns.db")
        try:
            self.assertGreater(conn.execute("SELECT sum(tax_minor) FROM OrderLine").fetchone()[0],0)
            self.assertGreater(conn.execute("SELECT sum(fee_minor) FROM RefundObligation").fetchone()[0],0)
        finally: conn.close()
        self.assertEqual(basis_points(101,5000),51)
        self.assertEqual(allocate_proportional(2,[1,1,1]),[1,1,0])

    def test_no_deliberate_truth_oracle_labels_exported(self):
        dataset=self.bundle()
        self.assertFalse(list(dataset.glob("ground_truth*")))
        attempts=json.loads((dataset/"json/ActionAttempt.json").read_text())
        for a in attempts: self.assertFalse({"issue_type","ground_truth","expected_outcome"}&set(a))

    def test_reexport_has_identical_business_files(self):
        dataset=self.bundle(); other=self.root/"exported"
        reexport(dataset,other)
        self.assertEqual(compare_datasets(dataset,other)["status"],"PASS")
        original=json.loads((dataset/"manifest.json").read_text())
        exported=json.loads((other/"manifest.json").read_text())
        self.assertEqual(original['generator_source_sha256'],generator_source_fingerprint())
        self.assertEqual(exported['generator_source_sha256'],original['generator_source_sha256'])

    def test_reexport_does_not_invent_historical_source_fingerprint(self):
        dataset=self.bundle(); manifest=dataset/"manifest.json"
        value=json.loads(manifest.read_text(encoding="utf-8")); value.pop('generator_source_sha256')
        manifest.write_text(canonical_json(value),encoding="utf-8",newline="\n")
        other=self.root/"old_source_export"; reexport(dataset,other)
        exported=json.loads((other/"manifest.json").read_text(encoding="utf-8"))
        self.assertIsNone(exported['generator_source_sha256'])
        self.assertEqual(compare_datasets(dataset,other)['generator_source_identity'],'UNAVAILABLE')

    def test_actual_rehash_detects_artifact_tampering(self):
        left=self.bundle("left"); right=self.bundle("right")
        with (right/"json/Customer.json").open("a") as stream: stream.write(" ")
        self.assertEqual(compare_datasets(left,right)["status"],"FAIL")

    def test_validator_detects_corrupted_financial_evidence(self):
        dataset=self.bundle(); conn=connect(dataset/"returns.db")
        try:
            conn.execute("DROP TRIGGER OrderLine_freeze_referenced_evidence")
            # Keep local paid CHECK valid while introducing incorrect configured tax.
            conn.execute("UPDATE OrderLine SET tax_minor=tax_minor+1,paid_minor=paid_minor+1 WHERE id=(SELECT min(id) FROM OrderLine)")
            result=validate(conn,tiny())
            self.assertEqual(result["status"],"FAIL")
            self.assertGreater(next(m for m in result["metrics"] if m["check_id"]=="LINE_FINANCIALS")["numerator"],0)
        finally: conn.close()

    def test_orphan_reference_produces_structured_validation_failure(self):
        dataset=self.bundle(); conn=connect(dataset/"returns.db")
        try:
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute("DROP TRIGGER ReturnRequest_immutable_order_id")
            conn.execute("UPDATE ReturnRequest SET order_id='ORD-2026-999999' WHERE id=(SELECT min(id) FROM ReturnRequest)")
            conn.execute("PRAGMA foreign_keys=ON")
        finally: conn.close()
        result=validate_dataset(dataset)
        self.assertEqual(result["status"],"FAIL")
        fk=next(m for m in result["metrics"] if m["check_id"]=="FK_INTEGRITY")
        self.assertEqual(fk["numerator"],1)
        self.assertEqual(fk["status"],"FAIL")
        self.assertIn("prevent",result["incomplete_checks_reason"])
        self.assertNotIn("ELIGIBILITY_REPLAY",{m["check_id"] for m in result["metrics"]})

    def test_legacy_v1_snapshot_validation_does_not_modify_or_claim_reproduction(self):
        dataset=self.bundle(); path=dataset/"configuration.json"
        config=json.loads(path.read_text(encoding="utf-8"))
        missing=("coverage_strata","order_line_weights","return_reason_weights","ordinary_condition_weights","damage_condition_weights")
        for name in missing: config.pop(name)
        path.write_text(canonical_json(config),encoding="utf-8",newline="\n")
        original=path.read_bytes()
        result=validate_dataset(dataset)
        self.assertEqual(result["status"],"PASS")
        compatibility=result["configuration_compatibility"]
        self.assertEqual(set(compatibility["validation_only_defaults"]),set(missing))
        self.assertFalse(compatibility["snapshot_modified"])
        self.assertFalse(compatibility["regeneration_of_historical_output_verified"])
        self.assertEqual(path.read_bytes(),original)
        with self.assertRaisesRegex(ValueError,"validation is supported but re-export is disabled"):
            reexport(dataset,self.root/"legacy_export")
        self.assertFalse((self.root/"legacy_export").exists())

    def test_overallocated_inspection_counts_each_affected_disposition(self):
        # Independent structural corruption in an isolated throwaway dataset;
        # no pre-inspection restock or Phase 4 anomaly is created.
        dataset=self.bundle(); conn=connect(dataset/"returns.db")
        try:
            d=conn.execute("SELECT * FROM InventoryDisposition WHERE action='RESTOCK' AND state='ACCEPTED' ORDER BY id LIMIT 1").fetchone()
            self.assertIsNotNone(d)
            conn.execute("DROP TRIGGER accepted_disposition_guard_INSERT")
            conn.execute("INSERT INTO InventoryDisposition VALUES(?,?,?,?,?,?,?,?)",
                ('DSP-2026-999999',d['return_line_id'],d['inspection_id'],'RESTOCK',1,d['decided_at'],'TEST','ACCEPTED'))
        finally: conn.close()
        report=validate_dataset(dataset)
        metric=next(m for m in report['metrics'] if m['check_id']=='DISPOSITION_PREREQUISITES')
        self.assertEqual(metric['numerator'],2)
        self.assertLessEqual(metric['numerator'],metric['denominator'])

    def test_duplicate_movements_count_each_affected_movement(self):
        dataset=self.bundle(); conn=connect(dataset/"returns.db")
        try:
            # TEMP view deliberately presents two movement rows for one decision;
            # the persistent dataset and its UNIQUE constraint remain untouched.
            conn.execute('''CREATE TEMP VIEW InventoryMovement AS
                SELECT * FROM main.InventoryMovement UNION ALL
                SELECT 'MOV-2026-999999',disposition_id,quantity,moved_at FROM main.InventoryMovement
                WHERE id=(SELECT min(id) FROM main.InventoryMovement)''')
            report=validate(conn,tiny())
            metric=next(m for m in report['metrics'] if m['check_id']=='PHYSICAL_MOVEMENTS')
            self.assertEqual(metric['numerator'],2)
            self.assertLessEqual(metric['numerator'],metric['denominator'])
        finally: conn.close()

    def test_pending_rejected_exchange_metric_counts_each_request_once(self):
        dataset=self.bundle(); conn=connect(dataset/"returns.db")
        try:
            target=conn.execute('''SELECT r.id FROM ReturnRequest r JOIN ReturnLine l ON l.request_id=r.id
                JOIN RefundObligation o ON o.return_line_id=l.id WHERE r.state='CLOSED' ORDER BY r.id LIMIT 1''').fetchone()[0]
            conn.execute(f'''CREATE TEMP VIEW ReturnRequest AS SELECT id,order_id,policy_id,requested_at,
                CASE WHEN id='{target}' THEN 'EXCHANGE' ELSE resolution END AS resolution,override_reason,
                CASE WHEN id='{target}' THEN 'REJECTED' ELSE state END AS state FROM main.ReturnRequest''')
            report=validate(conn,tiny())
            metric=next(m for m in report['metrics'] if m['check_id']=='PENDING_REJECTED_EXCHANGE')
            self.assertEqual(metric['numerator'],1)
        finally: conn.close()

    def test_aggregate_progress_metric_counts_each_request_once(self):
        dataset=self.bundle(); conn=connect(dataset/"returns.db")
        try:
            target=conn.execute("SELECT id FROM ReturnRequest WHERE state='INSPECTED' AND resolution='EXCHANGE' ORDER BY id LIMIT 1").fetchone()[0]
            conn.execute(f'''CREATE TEMP VIEW ReturnRequest AS SELECT id,order_id,policy_id,requested_at,resolution,override_reason,
                CASE WHEN id='{target}' THEN 'CLOSED' ELSE state END AS state FROM main.ReturnRequest''')
            report=validate(conn,tiny())
            metric=next(m for m in report['metrics'] if m['check_id']=='AGGREGATE_REQUEST_PROGRESS')
            self.assertEqual(metric['numerator'],1)
        finally: conn.close()

    def test_zero_requests_custom_scale(self):
        config=resolve_config(scale="custom",counts={"orders":3,"requests":0,"return_lines":0})
        dataset=self.bundle(config=config)
        self.assertEqual(validate_dataset(dataset)["row_counts"]["ReturnRequest"],0)
        self.assertEqual(validate_dataset(dataset)["status"],"PASS")


# Imported here avoids obscuring the generator's production dependency graph.
from returns_engine.validation import validate


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.path=Path(self.temp.name)/"approval.db"
        self.conn=connect(self.path); initialize(self.conn); approval_fixture(self.conn)
        self.config=tiny()

    def tearDown(self): self.conn.close(); self.temp.cleanup()

    def test_repeated_approvals_do_not_overreserve(self):
        _,first=authorize_request(self.conn,"RMA-2026-000001",self.config)
        _,second=authorize_request(self.conn,"RMA-2026-000002",self.config)
        self.assertEqual([first[0]["eligible_quantity"],second[0]["eligible_quantity"]],[2,1])
        self.assertEqual(reserved_quantity(self.conn,"ORL-2026-000001"),3)
        with self.assertRaises(ValueError): authorize_request(self.conn,"RMA-2026-000001",self.config)

    def test_concurrent_approvals_are_serialized(self):
        errors=[]
        def approve(identifier):
            conn=connect(self.path)
            try: authorize_request(conn,identifier,self.config)
            except Exception as exc: errors.append(str(exc))
            finally: conn.close()
        threads=[threading.Thread(target=approve,args=(f"RMA-2026-{i:06d}",)) for i in (1,2)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(errors,[])
        self.assertEqual(reserved_quantity(self.conn,"ORL-2026-000001"),3)

    def test_cancelled_unused_authorization_releases_quantity(self):
        header,_=authorize_request(self.conn,"RMA-2026-000001",self.config)
        cancel_authorization(self.conn,header,"2026-09-02T01:00:00Z")
        self.assertEqual(reserved_quantity(self.conn,"ORL-2026-000001"),0)
        _,decision=authorize_request(self.conn,"RMA-2026-000002",self.config)
        self.assertEqual(decision[0]["eligible_quantity"],3)

    def test_window_boundary_exclusions_and_override_authority(self):
        self.conn.execute("UPDATE ReturnRequest SET requested_at='2026-10-01T00:00:00Z' WHERE id='RMA-2026-000001'")
        line="RMAL-RMA-2026-000001-01"
        self.assertEqual(evaluate_line(self.conn,line,self.config)["eligible_quantity"],2)
        self.conn.execute("UPDATE ReturnRequest SET requested_at='2026-10-02T00:00:00Z' WHERE id='RMA-2026-000001'")
        self.assertEqual(evaluate_line(self.conn,line,self.config)["reason_code"],"WINDOW_EXPIRED")
        self.conn.execute("UPDATE ReturnRequest SET override_reason='untrusted note' WHERE id='RMA-2026-000001'")
        self.assertEqual(evaluate_line(self.conn,line,self.config)["reason_code"],"OVERRIDE_UNSUPPORTED")
        self.conn.execute("UPDATE Product SET category='PERSONAL_CARE'")
        self.assertEqual(evaluate_line(self.conn,"RMAL-RMA-2026-000002-01",self.config)["reason_code"],"CATEGORY_EXCLUDED")

    def test_requested_excess_is_blocked_not_silently_paid(self):
        self.conn.execute("UPDATE ReturnLine SET requested_quantity=4 WHERE request_id='RMA-2026-000001'")
        header,decision=authorize_request(self.conn,"RMA-2026-000001",self.config)
        self.assertIsNone(header)
        self.assertEqual(decision[0]["reason_code"],"QTY_EXCEEDS_PURCHASED")
        self.assertEqual(self.conn.execute("SELECT count(*) FROM Refund").fetchone()[0],0)

    def test_shipped_reservation_cannot_be_cancelled(self):
        header,_=authorize_request(self.conn,"RMA-2026-000001",self.config)
        aid=self.conn.execute("SELECT id FROM AuthorizationLine").fetchone()[0]
        self.conn.execute("INSERT INTO ReturnShipment VALUES('RTS-2026-000001','2026-09-02T00:00:00Z',NULL,NULL,'CREATED')")
        self.conn.execute("INSERT INTO ShipmentLine VALUES('SHL-2026-000001','RTS-2026-000001',?,2,0)",(aid,))
        with self.assertRaises(ValueError): cancel_authorization(self.conn,header,"2026-09-03T00:00:00Z")
        self.assertEqual(reserved_quantity(self.conn,"ORL-2026-000001"),2)
