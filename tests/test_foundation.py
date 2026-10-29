import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from returns_engine.events import record_event
from returns_engine.ids import allocate_id, make_id, return_line_id
from returns_engine.model import TABLES, TARGETS
from returns_engine.money import minor_units, allocate_minor
from returns_engine.schema import connect, initialize, transaction

T = "2026-10-01T00:00:00Z"
LATER = "2026-10-02T00:00:00Z"


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "fresh.db"
        self.db = connect(self.path)
        initialize(self.db)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def add(self, table, **values):
        columns = ",".join('"'+k+'"' for k in values)
        placeholders = ",".join("?" for _ in values)
        self.db.execute(f'INSERT INTO "{table}"({columns}) VALUES({placeholders})', tuple(values.values()))

    def baseline(self):
        self.add("Customer", id="CUS-2026-000001", synthetic_name="Synthetic customer", state="ACTIVE", created_at=T)
        self.add("Product", id="PRD-2026-000001", category="CLOTHING", description="Synthetic shirt")
        self.add("ReturnPolicy", id="POL-2026-000001", window_days=30, excluded_categories_json='[]', fee_bps=0, effective_from=T)
        self.add("Order", id="ORD-2026-000001", customer_id="CUS-2026-000001", currency="INR", placed_at=T, delivered_at=T, shipping_paid_minor=0, state="DELIVERED")
        self.add("OrderLine", id="ORL-2026-000001", order_id="ORD-2026-000001", product_id="PRD-2026-000001", quantity=2, unit_price_minor=100, line_discount_minor=0, order_discount_allocated_minor=0, tax_minor=0, paid_minor=200)
        self.add("ReturnRequest", id="RMA-2026-000001", order_id="ORD-2026-000001", policy_id="POL-2026-000001", requested_at=T, resolution="REFUND", state="REQUESTED")
        self.add("ReturnLine", id=return_line_id("RMA-2026-000001", 1), request_id="RMA-2026-000001", order_line_id="ORL-2026-000001", line_sequence=1, requested_quantity=2, reason_code="SIZE", state="REQUESTED")

    def inspected(self):
        self.baseline()
        self.add("ReturnAuthorization", id="RAU-2026-000001", request_id="RMA-2026-000001", issued_at=T, state="ISSUED")
        self.add("AuthorizationLine", id="RAL-2026-000001", authorization_id="RAU-2026-000001", return_line_id=return_line_id("RMA-2026-000001",1), approved_quantity=2)
        self.add("ReturnShipment", id="RTS-2026-000001", created_at=T, dispatched_at=T, delivered_at=T, state="DELIVERED")
        self.add("ShipmentLine", id="SHL-2026-000001", shipment_id="RTS-2026-000001", authorization_line_id="RAL-2026-000001", shipped_quantity=2, received_quantity=2)
        self.add("Inspection", id="INS-2026-000001", shipment_line_id="SHL-2026-000001", inspected_quantity=2, condition="SELLABLE", inspected_at=T, state="FINALIZED")
        self.add("RefundObligation", id="RFO-2026-000001", return_line_id=return_line_id("RMA-2026-000001",1), inspection_id="INS-2026-000001", entitlement_minor=200, fee_minor=0)

    def refund(self, counter=1, key="logical-payment", amount=100, state="SUCCEEDED"):
        self.add("Refund", id=make_id("Refund",counter), obligation_id="RFO-2026-000001", payment_key=key,
            requested_minor=amount, paid_minor=amount if state=="SUCCEEDED" else 0, attempted_at=T, reason_code="OK" if state=="SUCCEEDED" else "BLOCKED", state=state)

    def disposition(self, *, inspection="INS-2026-000001", state="ACCEPTED", quantity=2, counter=1):
        self.add("InventoryDisposition", id=make_id("InventoryDisposition",counter), return_line_id=return_line_id("RMA-2026-000001",1), inspection_id=inspection,
            action="RESTOCK", quantity=quantity, decided_at=T, reason_code="OK", state=state)

    def event(self, **overrides):
        kwargs = dict(event_type="STATE_CHANGED", occurred_at=T, reason_code="TEST", correlation_id="test-transaction", new_state="INACTIVE")
        kwargs.update(overrides)
        return record_event(self.db,"Customer","CUS-2026-000001",**kwargs)

    def test_empty_schema_and_idempotent_initialize(self):
        initialize(self.db)
        actual = {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(actual, set(TABLES) | {"SchemaVersion", "IdSequence"})
        self.assertEqual(self.db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(list(self.db.execute("PRAGMA foreign_key_check")), [])

    def test_every_connection_enforces_foreign_keys(self):
        other = connect(self.path)
        try:
            self.assertEqual(other.execute("PRAGMA foreign_keys").fetchone()[0],1)
        finally:
            other.close()
        with self.assertRaises(sqlite3.IntegrityError):
            self.add("Order", id="ORD-2026-000001", customer_id="CUS-2026-999999", currency="INR", placed_at=T, shipping_paid_minor=0, state="PLACED")

    def test_pk_uniqueness_required_fields_and_enums(self):
        self.baseline()
        for values in (
            dict(id="CUS-2026-000001", synthetic_name="Duplicate", state="ACTIVE", created_at=T),
            dict(id="CUS-2026-000002", state="ACTIVE", created_at=T),
            dict(id="CUS-2026-000002", synthetic_name="Bad", state="UNKNOWN", created_at=T),
            dict(id="CUS-2026-000002", synthetic_name="", state="ACTIVE", created_at=T),
        ):
            with self.subTest(values=values), self.assertRaises(sqlite3.IntegrityError):
                self.add("Customer", **values)

    def test_required_id_examples_and_bounds(self):
        for entity,prefix in (("Order","ORD"),("ReturnRequest","RMA"),("ReturnShipment","RTS"),("Refund","REF")):
            self.assertEqual(make_id(entity,1),prefix+"-2026-000001")
            self.assertEqual(make_id(entity,999999),prefix+"-2026-999999")
            for value in (0,-1,1000000,True,1.5,"1"):
                with self.subTest(entity=entity,value=value), self.assertRaises(ValueError): make_id(entity,value)
        self.assertEqual(return_line_id("RMA-2026-000001",1),"RMAL-RMA-2026-000001-01")
        self.assertEqual(return_line_id("RMA-2026-999999",99),"RMAL-RMA-2026-999999-99")
        for parent,seq in (("2026-000001",1),("RMA-2025-000001",1),("RMA-2026-000000",1),("RMA-2026-000001",0),("RMA-2026-000001",100),("RMA-2026-000001",True)):
            with self.assertRaises(ValueError): return_line_id(parent,seq)

    def test_sql_identifier_format_embedding_and_immutability(self):
        self.baseline()
        with self.assertRaises(sqlite3.IntegrityError):
            self.add("Customer",id="CUS-2026-000000",synthetic_name="Bad",state="ACTIVE",created_at=T)
        for identifier in ("RMAL-2026-000001-02","RMAL-RMA-2026-000002-02"):
            with self.assertRaises(sqlite3.IntegrityError):
                self.add("ReturnLine",id=identifier,request_id="RMA-2026-000001",order_line_id="ORL-2026-000001",line_sequence=2,requested_quantity=1,reason_code="SIZE",state="REQUESTED")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE Customer SET id='CUS-2026-000002'")

    def test_allocation_increments_rollback_and_existing_ids(self):
        self.baseline()
        with self.assertRaises(RuntimeError): allocate_id(self.db,"Customer")
        with transaction(self.db):
            self.assertEqual(allocate_id(self.db,"Customer"),"CUS-2026-000002")
            self.assertEqual(allocate_id(self.db,"Customer"),"CUS-2026-000003")
        with self.assertRaises(ValueError):
            with transaction(self.db):
                self.assertEqual(allocate_id(self.db,"Customer"),"CUS-2026-000004")
                raise ValueError("rollback")
        with transaction(self.db): self.assertEqual(allocate_id(self.db,"Customer"),"CUS-2026-000004")

    def test_two_writers_allocate_distinct_ids(self):
        result, errors = [], []
        def writer():
            conn = connect(self.path)
            try:
                with transaction(conn): result.append(allocate_id(conn,"Customer"))
            except Exception as exc: errors.append(exc)
            finally: conn.close()
        threads=[threading.Thread(target=writer) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(errors,[])
        self.assertEqual(set(result),{"CUS-2026-000001","CUS-2026-000002"})

    def test_valid_optional_links_and_pending_states(self):
        self.baseline()
        self.add("ReturnShipment",id="RTS-2026-000001",created_at=T,state="CREATED")
        self.add("RefundObligation",id="RFO-2026-000001",return_line_id=return_line_id("RMA-2026-000001",1),entitlement_minor=0,fee_minor=0)
        self.refund(amount=999,state="REJECTED")
        self.disposition(inspection=None,state="REJECTED")
        self.assertEqual(list(self.db.execute("PRAGMA foreign_key_check")),[])

    def test_cross_order_line_rejected(self):
        self.baseline()
        self.add("Order",id="ORD-2026-000002",customer_id="CUS-2026-000001",currency="INR",placed_at=T,shipping_paid_minor=0,state="PLACED")
        self.add("ReturnRequest",id="RMA-2026-000002",order_id="ORD-2026-000002",policy_id="POL-2026-000001",requested_at=T,resolution="REFUND",state="REQUESTED")
        with self.assertRaises(sqlite3.IntegrityError):
            self.add("ReturnLine",id=return_line_id("RMA-2026-000002",1),request_id="RMA-2026-000002",order_line_id="ORL-2026-000001",line_sequence=1,requested_quantity=1,reason_code="SIZE",state="REQUESTED")

    def test_strict_integer_money_and_arithmetic(self):
        self.baseline()
        # Use an unreferenced line so the evidence-freeze trigger cannot mask
        # a broken numeric constraint.
        self.add("OrderLine",id="ORL-2026-000002",order_id="ORD-2026-000001",product_id="PRD-2026-000001",quantity=2,unit_price_minor=100,line_discount_minor=0,order_discount_allocated_minor=0,tax_minor=0,paid_minor=200)
        for expression in ("unit_price_minor=1.5","paid_minor=201","line_discount_minor=201","quantity=0"):
            with self.subTest(expression=expression), self.assertRaises(sqlite3.IntegrityError):
                self.db.execute("UPDATE OrderLine SET "+expression+" WHERE id='ORL-2026-000002'")
        self.assertEqual(minor_units("1.005"),101)
        self.assertEqual(allocate_minor(100,3),(34,33,33))
        with self.assertRaises(TypeError): minor_units(1.005)
        for value in ("NaN","Infinity","-1"):
            with self.assertRaises(ValueError): minor_units(value)

    def test_event_history_atomic_and_append_only(self):
        self.baseline()
        self.event(event_type="CREATED",new_state=None)
        identifier=self.event()
        self.assertEqual(self.db.execute("SELECT state FROM Customer").fetchone()[0],"INACTIVE")
        self.assertEqual(self.db.execute("SELECT previous_state,new_state FROM EventLog WHERE id=?",(identifier,)).fetchone()[:],("ACTIVE","INACTIVE"))
        for sql in ("UPDATE EventLog SET reason_code='CHANGED'","DELETE FROM EventLog","UPDATE Customer SET state='ACTIVE'"):
            with self.assertRaises(sqlite3.IntegrityError): self.db.execute(sql)
        self.db.close(); self.db=connect(self.path)
        self.assertEqual(self.db.execute("SELECT count(*) FROM EventLog").fetchone()[0],2)
        self.assertEqual(self.db.execute("SELECT entity_type,entity_id FROM EventHistory LIMIT 1").fetchone()[:],("Customer","CUS-2026-000001"))

    def test_invalid_event_transition_time_and_reference(self):
        self.baseline()
        for kwargs in (dict(new_state="CLOSED"),dict(occurred_at="2026-02-30T00:00:00Z")):
            with self.assertRaises(ValueError): self.event(**kwargs)
        with self.assertRaises(ValueError): record_event(self.db,"Customer","CUS-2026-999999",event_type="OBSERVED",occurred_at=T,reason_code="TEST",correlation_id="x")
        self.assertEqual(self.db.execute("SELECT count(*) FROM EventLog").fetchone()[0],0)
        self.event(occurred_at=LATER)
        with self.assertRaises(sqlite3.IntegrityError): self.event(new_state="ACTIVE",occurred_at=T)

    def test_event_typed_target_requires_exactly_one_real_reference(self):
        self.baseline()
        base=dict(id="EVT-2026-000001",event_type="OBSERVED",occurred_at=T,reason_code="TEST",correlation_id="x")
        for targets in ({},{"Customer_id":"CUS-2026-999999"},{"Customer_id":"CUS-2026-000001","Order_id":"ORD-2026-000001"}):
            with self.assertRaises(sqlite3.IntegrityError): self.add("EventLog",**base,**targets)

    def test_blocked_actions_have_no_ground_truth_inputs(self):
        self.baseline()
        self.add("ActionAttempt",id="ATT-2026-000001",ReturnLine_id=return_line_id("RMA-2026-000001",1),action="AUTHORIZE",payload_json='{"quantity":999}',decision="BLOCKED",reason_code="QTY_EXCEEDS_REMAINING",attempted_at=T,correlation_id="x")
        names={r[1] for r in self.db.execute("PRAGMA table_info(ActionAttempt)")}
        self.assertFalse(names & {"ground_truth","issue_type","expected_outcome"})
        self.assertEqual(self.db.execute("SELECT count(*) FROM ReturnAuthorization").fetchone()[0],0)

    def test_excess_duplicate_and_cumulative_refund_blocked(self):
        self.inspected()
        self.refund()
        for counter,key,amount in ((2,"logical-payment",100),(2,"different-key",101)):
            with self.assertRaises(sqlite3.IntegrityError): self.refund(counter,key,amount)
        self.refund(2,"logical-payment",999,"REJECTED")
        self.refund(3,"different-key",100)
        self.assertEqual(self.db.execute("SELECT sum(paid_minor) FROM Refund").fetchone()[0],200)

    def test_failed_retry_can_succeed_once(self):
        self.inspected()
        self.refund(1,"retry",100,"FAILED")
        self.refund(2,"retry",100)
        with self.assertRaises(sqlite3.IntegrityError): self.refund(3,"retry",100)

    def test_pending_refund_transition_rolls_back_event_on_excess(self):
        self.inspected()
        self.refund(1,"pending",300,"REQUESTED")
        with self.assertRaises(sqlite3.IntegrityError):
            record_event(self.db,"Refund","REF-2026-000001",event_type="STATE_CHANGED",occurred_at=T,reason_code="OK",correlation_id="x",new_state="SUCCEEDED",changes={"paid_minor":300,"reason_code":"OK"})
        self.assertEqual(self.db.execute("SELECT count(*) FROM EventLog").fetchone()[0],0)
        self.assertEqual(self.db.execute("SELECT state,paid_minor FROM Refund").fetchone()[:],("REQUESTED",0))

    def test_preinspection_restock_and_refund_cannot_post(self):
        self.baseline()
        self.add("RefundObligation",id="RFO-2026-000001",return_line_id=return_line_id("RMA-2026-000001",1),entitlement_minor=200,fee_minor=0)
        with self.assertRaises(sqlite3.IntegrityError): self.refund()
        self.refund(1,"blocked",100,"REJECTED")
        with self.assertRaises(sqlite3.IntegrityError): self.disposition(inspection=None)
        self.disposition(inspection=None,state="REJECTED")
        with self.assertRaises(sqlite3.IntegrityError):
            self.add("InventoryMovement",id="MOV-2026-000001",disposition_id="DSP-2026-000001",quantity=2,moved_at=T)

    def test_disposition_is_not_inventory_movement(self):
        self.inspected()
        self.disposition()
        self.assertEqual(self.db.execute("SELECT count(*) FROM InventoryMovement").fetchone()[0],0)
        self.add("InventoryMovement",id="MOV-2026-000001",disposition_id="DSP-2026-000001",quantity=2,moved_at=T)
        with self.assertRaises(sqlite3.IntegrityError):
            self.add("InventoryMovement",id="MOV-2026-000002",disposition_id="DSP-2026-000001",quantity=2,moved_at=T)
        with self.assertRaises(sqlite3.IntegrityError): self.disposition(counter=2,quantity=1)

    def test_inspection_cannot_exceed_receipts(self):
        self.inspected()
        with self.assertRaises(sqlite3.IntegrityError):
            self.add("Inspection",id="INS-2026-000002",shipment_line_id="SHL-2026-000001",inspected_quantity=1,condition="SELLABLE",inspected_at=T,state="FINALIZED")

    def test_transactions_rollback_and_nested_savepoint(self):
        with transaction(self.db):
            self.add("Product",id="PRD-2026-000001",category="X",description="X")
            with self.assertRaises(ValueError):
                with transaction(self.db):
                    self.add("Product",id="PRD-2026-000002",category="X",description="X")
                    raise ValueError("rollback inner")
        self.assertEqual(self.db.execute("SELECT count(*) FROM Product").fetchone()[0],1)

    def test_split_shipments_and_multiple_inspection_batches(self):
        self.inspected()
        # A second requested line can be split between two independent shipments.
        self.add("OrderLine",id="ORL-2026-000002",order_id="ORD-2026-000001",product_id="PRD-2026-000001",quantity=3,unit_price_minor=100,line_discount_minor=0,order_discount_allocated_minor=0,tax_minor=0,paid_minor=300)
        line=return_line_id("RMA-2026-000001",2)
        self.add("ReturnLine",id=line,request_id="RMA-2026-000001",order_line_id="ORL-2026-000002",line_sequence=2,requested_quantity=3,reason_code="SIZE",state="REQUESTED")
        self.add("AuthorizationLine",id="RAL-2026-000002",authorization_id="RAU-2026-000001",return_line_id=line,approved_quantity=3)
        for counter in (2,3):
            self.add("ReturnShipment",id=make_id("ReturnShipment",counter),created_at=T,dispatched_at=T,delivered_at=T,state="DELIVERED")
            quantity=2 if counter==2 else 1
            self.add("ShipmentLine",id=make_id("ShipmentLine",counter),shipment_id=make_id("ReturnShipment",counter),authorization_line_id="RAL-2026-000002",shipped_quantity=quantity,received_quantity=quantity)
            self.add("Inspection",id=make_id("Inspection",counter),shipment_line_id=make_id("ShipmentLine",counter),inspected_quantity=1,condition="SELLABLE",inspected_at=T,state="FINALIZED")
        self.add("Inspection",id="INS-2026-000004",shipment_line_id="SHL-2026-000002",inspected_quantity=1,condition="REPAIRABLE",inspected_at=T,state="FINALIZED")
        self.assertEqual(self.db.execute("SELECT sum(shipped_quantity) FROM ShipmentLine WHERE authorization_line_id='RAL-2026-000002'").fetchone()[0],3)

    def test_used_financial_and_quantity_evidence_cannot_drift(self):
        self.inspected()
        self.refund()
        for sql in ("UPDATE OrderLine SET quantity=3,paid_minor=300", "UPDATE ShipmentLine SET received_quantity=0",
                    "UPDATE AuthorizationLine SET approved_quantity=1", "UPDATE ReturnPolicy SET window_days=999",
                    "UPDATE RefundObligation SET entitlement_minor=999", "UPDATE Refund SET paid_minor=0"):
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError): self.db.execute(sql)

    def test_allocator_exhaustion_and_unknown_entity(self):
        with transaction(self.db):
            self.db.execute("INSERT INTO IdSequence VALUES('Refund',999998)")
            self.assertEqual(allocate_id(self.db,"Refund"),"REF-2026-999999")
            with self.assertRaises(sqlite3.IntegrityError): allocate_id(self.db,"Refund")
            with self.assertRaises(ValueError): allocate_id(self.db,"Bogus")

    def test_pending_refund_success_transition_is_atomic(self):
        self.inspected()
        self.refund(1,"pending",100,"REQUESTED")
        record_event(self.db,"Refund","REF-2026-000001",event_type="STATE_CHANGED",occurred_at=T,reason_code="OK",correlation_id="x",new_state="SUCCEEDED",changes={"paid_minor":100,"reason_code":"OK"})
        self.assertEqual(self.db.execute("SELECT state,paid_minor FROM Refund").fetchone()[:],("SUCCEEDED",100))

    def test_schema_sql_standalone_reload(self):
        from returns_engine.schema import schema_sql
        other=connect()
        try:
            other.executescript(schema_sql())
            self.assertEqual(other.execute("PRAGMA integrity_check").fetchone()[0],"ok")
            self.assertEqual(list(other.execute("PRAGMA foreign_key_check")),[])
        finally: other.close()

    def test_sql_rejects_all_prescribed_header_id_misspellings(self):
        self.inspected()
        self.refund(state="REQUESTED")
        for table, identifier in (("Order","ORD-2026-000001"),("ReturnRequest","RMA-2026-000001"),
                                   ("ReturnShipment","RTS-2026-000001"),("Refund","REF-2026-000001")):
            row=dict(self.db.execute('SELECT * FROM "'+table+'" WHERE id=?',(identifier,)).fetchone())
            for invalid in (identifier.replace("2026","2025"),identifier[:-1],identifier+"1",identifier[:-6]+"000000"):
                row["id"]=invalid
                with self.subTest(table=table,id=invalid), self.assertRaises(sqlite3.IntegrityError): self.add(table,**row)

    def test_every_fk_is_indexed_and_all_pks_are_required(self):
        for table in TABLES:
            fields=list(self.db.execute('PRAGMA table_info("'+table+'")'))
            primary=[r for r in fields if r[5]]
            self.assertEqual([(r[1],r[3]) for r in primary],[("id",1)])
            for fk in self.db.execute('PRAGMA foreign_key_list("'+table+'")'):
                self.assertEqual(fk[5:7],("RESTRICT","RESTRICT"))
                self.assertIsNotNone(self.db.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",("ix_"+table+"_"+fk[3],)).fetchone())

    def test_dictionary_matches_every_actual_column(self):
        from returns_engine.dictionary import render_dictionary
        dictionary=render_dictionary()
        for table, fields in TABLES.items():
            actual=[r[1] for r in self.db.execute('PRAGMA table_info("'+table+'")')]
            self.assertEqual(actual,[f.name for f in fields])
            for name in actual: self.assertIn(f"### {table}.{name}\n",dictionary)
        self.assertEqual((Path(__file__).parents[1]/"docs/data_dictionary.md").read_text(encoding="utf-8"),dictionary)


if __name__ == "__main__": unittest.main()
