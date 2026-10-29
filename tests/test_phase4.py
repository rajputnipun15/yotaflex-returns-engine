import tempfile
import unittest
from pathlib import Path
from scripts.phase4_scenarios import run_one

class Phase4Scenarios(unittest.TestCase):
    def check_case(self, case, control, decision, reason, effect, amount):
        with tempfile.TemporaryDirectory() as tmp:
            result=run_one(Path(tmp)/'fixture.db',case,control)
            self.assertEqual((result['observed_decision'],result['observed_reason_code']),(decision,reason))
            self.assertEqual(result['final'][effect]-result['initial'][effect],amount)
            self.assertEqual(result['integrity_check'],'ok')
            self.assertEqual(result['foreign_key_violations'],[])
            if not control:
                self.assertEqual(result['final']['paid_minor'],result['initial']['paid_minor'])
                self.assertEqual(result['final']['restocked_units'],result['initial']['restocked_units'])
                if case in ('excess','duplicate','inventory'):
                    self.assertEqual(result['final']['events'],result['initial']['events'])
    def test_quantity_negative(self): self.check_case('quantity',False,'BLOCKED','NO_REMAINING_QUANTITY','reserved_units',0)
    def test_quantity_partial_control(self): self.check_case('quantity',True,'ALLOWED','PARTIAL_REMAINING_QUANTITY','reserved_units',1)
    def test_excess_negative(self): self.check_case('excess',False,'BLOCKED','REFUND_SUCCESS_GUARD','paid_minor',0)
    def test_refund_remaining_control(self): self.check_case('excess',True,'ALLOWED','REFUND_SUCCEEDED','paid_minor',100)
    def test_inventory_negative(self): self.check_case('inventory',False,'BLOCKED','MOVEMENT_REQUIRES_ACCEPTED_DECISION','restocked_units',0)
    def test_inventory_sellable_control(self): self.check_case('inventory',True,'ALLOWED','RESTOCK_POSTED','restocked_units',2)
    def test_late_negative(self): self.check_case('late',False,'BLOCKED','WINDOW_EXPIRED','reserved_units',0)
    def test_window_boundary_control(self): self.check_case('late',True,'ALLOWED','ELIGIBLE','reserved_units',2)
    def test_duplicate_negative(self): self.check_case('duplicate',False,'BLOCKED','DUPLICATE_PAYMENT_KEY','paid_minor',0)
    def test_failed_retry_control(self): self.check_case('duplicate',True,'ALLOWED','REFUND_SUCCEEDED','paid_minor',100)
