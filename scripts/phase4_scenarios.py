"""Isolated adversarial exercises of the actual policy service and SQLite guards."""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

from returns_engine.config import resolve_config
from returns_engine.events import record_event
from returns_engine.ids import return_line_id
from returns_engine.policy import authorize_request, reserved_quantity
from returns_engine.schema import connect, initialize, transaction

T = '2026-10-01T00:00:00Z'
LATE = '2026-11-01T00:00:00Z'
BOUNDARY = '2026-10-31T00:00:00Z'
LINE = return_line_id('RMA-2026-000001', 1)

def add(db, table, *, event_at=None, **values):
    db.execute('INSERT INTO "'+table+'" ('+','.join('"'+x+'"' for x in values)+') VALUES ('+','.join('?' for _ in values)+')', tuple(values.values()))
    record_event(db, table, values['id'], event_type='CREATED', occurred_at=event_at or values.get('requested_at', T), reason_code='FIXTURE_CREATED', correlation_id=values['id'])

def fixture(db, requested_at=T):
    add(db,'Customer',id='CUS-2026-000001',synthetic_name='Fixture',state='ACTIVE',created_at=T)
    add(db,'Product',id='PRD-2026-000001',category='CLOTHING',description='Fixture')
    add(db,'ReturnPolicy',id='POL-2026-000001',window_days=30,excluded_categories_json='[]',fee_bps=0,effective_from=T)
    add(db,'Order',id='ORD-2026-000001',customer_id='CUS-2026-000001',currency='INR',placed_at=T,delivered_at=T,shipping_paid_minor=0,state='DELIVERED')
    add(db,'OrderLine',id='ORL-2026-000001',order_id='ORD-2026-000001',product_id='PRD-2026-000001',quantity=2,unit_price_minor=100,line_discount_minor=0,order_discount_allocated_minor=0,tax_minor=0,paid_minor=200)
    add(db,'ReturnRequest',id='RMA-2026-000001',order_id='ORD-2026-000001',policy_id='POL-2026-000001',requested_at=requested_at,resolution='REFUND',state='REQUESTED')
    add(db,'ReturnLine',event_at=requested_at,id=LINE,request_id='RMA-2026-000001',order_line_id='ORL-2026-000001',line_sequence=1,requested_quantity=2,reason_code='SIZE',state='REQUESTED')

def inspected(db, finalize=True):
    authorize_request(db,'RMA-2026-000001',resolve_config())
    transition(db,'ReturnRequest','RMA-2026-000001','IN_TRANSIT')
    transition(db,'ReturnLine',LINE,'SHIPPED')
    add(db,'ReturnShipment',id='RTS-2026-000001',created_at=T,dispatched_at=T,delivered_at=T,state='DELIVERED')
    add(db,'ShipmentLine',id='SHL-2026-000001',shipment_id='RTS-2026-000001',authorization_line_id='RAL-2026-000001',shipped_quantity=2,received_quantity=2)
    transition(db,'ReturnRequest','RMA-2026-000001','RECEIVED')
    transition(db,'ReturnLine',LINE,'RECEIVED')
    if finalize:
        add(db,'Inspection',id='INS-2026-000001',shipment_line_id='SHL-2026-000001',inspected_quantity=2,condition='SELLABLE',inspected_at=T,state='FINALIZED')
        transition(db,'ReturnRequest','RMA-2026-000001','INSPECTED')
        transition(db,'ReturnLine',LINE,'INSPECTED')
        add(db,'RefundObligation',id='RFO-2026-000001',return_line_id=LINE,inspection_id='INS-2026-000001',entitlement_minor=200,fee_minor=0)

def refund(db, ident, key, amount):
    add(db,'Refund',id=ident,obligation_id='RFO-2026-000001',payment_key=key,requested_minor=amount,paid_minor=0,attempted_at=T,reason_code=None,state='REQUESTED')

def transition(db, table, ident, state, **changes):
    return record_event(db,table,ident,event_type='STATE_CHANGED',occurred_at=T,reason_code='FIXTURE_ACTION',correlation_id=ident,new_state=state,changes=changes)

def snapshot(db):
    return {'paid_minor':db.execute('SELECT COALESCE(SUM(paid_minor),0) FROM Refund').fetchone()[0],
            'successful_refunds':db.execute("SELECT COUNT(*) FROM Refund WHERE state='SUCCEEDED'").fetchone()[0],
            'restocked_units':db.execute("SELECT COALESCE(SUM(m.quantity),0) FROM InventoryMovement m JOIN InventoryDisposition d ON d.id=m.disposition_id WHERE d.action='RESTOCK'").fetchone()[0],
            'reserved_units':reserved_quantity(db,'ORL-2026-000001'),
            'events':db.execute('SELECT COUNT(*) FROM EventLog').fetchone()[0]}

def run_one(path, case, control=False):
    db=connect(path); initialize(db)
    fixture(db, BOUNDARY if case=='late' and control else LATE if case=='late' else T)
    raw=None; reason=None; decision=None; attempted=None
    if case=='quantity':
        # The first approval reserves all units (one unit in the control), then a second request tries two.
        if control: db.execute('UPDATE ReturnLine SET requested_quantity=1 WHERE id=?',(LINE,))
        authorize_request(db,'RMA-2026-000001',resolve_config())
        add(db,'ReturnRequest',id='RMA-2026-000002',order_id='ORD-2026-000001',policy_id='POL-2026-000001',requested_at=T,resolution='REFUND',state='REQUESTED')
        line2=return_line_id('RMA-2026-000002',1)
        add(db,'ReturnLine',id=line2,request_id='RMA-2026-000002',order_line_id='ORL-2026-000001',line_sequence=1,requested_quantity=2,reason_code='SIZE',state='REQUESTED')
        before=snapshot(db); attempted={'operation':'authorize', 'request_id':'RMA-2026-000002','requested_units':2}
        _, ds=authorize_request(db,'RMA-2026-000002',resolve_config()); d=ds[0]
        decision='ALLOWED' if d['eligible_quantity'] else 'BLOCKED'; reason=d['reason_code']
    elif case=='late':
        before=snapshot(db); attempted={'operation':'authorize','request_id':'RMA-2026-000001','requested_at':BOUNDARY if control else LATE,'override':None}
        _, ds=authorize_request(db,'RMA-2026-000001',resolve_config()); d=ds[0]
        decision='ALLOWED' if d['eligible_quantity'] else 'BLOCKED'; reason=d['reason_code']
    else:
        inspected(db, finalize=(case!='inventory' or control))
        if case=='inventory':
            add(db,'InventoryDisposition',id='DSP-2026-000001',return_line_id=LINE,inspection_id='INS-2026-000001' if control else None,action='RESTOCK',quantity=2,decided_at=T,reason_code=None,state='PROPOSED')
            if control: transition(db,'InventoryDisposition','DSP-2026-000001','ACCEPTED',reason_code='SELLABLE')
            before=snapshot(db); attempted={'operation':'insert_inventory_movement','disposition_id':'DSP-2026-000001','units':2}
            try:
                with transaction(db):
                    add(db,'InventoryMovement',id='MOV-2026-000001',disposition_id='DSP-2026-000001',quantity=2,moved_at=T)
                decision,reason='ALLOWED','RESTOCK_POSTED'
            except sqlite3.IntegrityError as e:
                raw=str(e); decision,reason='BLOCKED', 'MOVEMENT_REQUIRES_ACCEPTED_DECISION' if raw=='movement_requires_accepted_decision' else 'UNCLASSIFIED_DATABASE_REJECTION'
        else:
            if case=='duplicate':
                refund(db,'REF-2026-000001','logical-payment',100)
                transition(db,'Refund','REF-2026-000001','FAILED' if control else 'SUCCEEDED',paid_minor=0 if control else 100,reason_code='PROVIDER_FAILURE' if control else 'PAID')
            refund(db,'REF-2026-000002','logical-payment' if case=='duplicate' else 'excess-payment',200 if case=='excess' and not control else 100)
            before=snapshot(db); amount=200 if case=='excess' and not control else 100
            if case=='excess':
                # A previous distinct successful payout consumes half the obligation.
                refund(db,'REF-2026-000001','prior-payment',100); transition(db,'Refund','REF-2026-000001','SUCCEEDED',paid_minor=100,reason_code='PAID')
                before=snapshot(db)
            attempted={'operation':'succeed_refund','refund_id':'REF-2026-000002','amount_minor':amount,'payment_key':'logical-payment' if case=='duplicate' else 'excess-payment'}
            try:
                transition(db,'Refund','REF-2026-000002','SUCCEEDED',paid_minor=amount,reason_code='PAID')
                decision,reason='ALLOWED','REFUND_SUCCEEDED'
            except sqlite3.IntegrityError as e:
                raw=str(e); decision='BLOCKED'
                reason={'refund_success_guard':'REFUND_SUCCESS_GUARD','UNIQUE constraint failed: Refund.payment_key':'DUPLICATE_PAYMENT_KEY'}.get(raw,'UNCLASSIFIED_DATABASE_REJECTION')
    after=snapshot(db)
    result={'scenario_id':case+('_control' if control else '_negative'),'attempted_operation':attempted,'initial':before,'final':after,'observed_decision':decision,'observed_reason_code':reason,'raw_database_error':raw,
            'integrity_check':db.execute('PRAGMA integrity_check').fetchone()[0], 'foreign_key_violations':[list(x) for x in db.execute('PRAGMA foreign_key_check')],
            'refund_states':[dict(x) for x in db.execute('SELECT id,payment_key,state,paid_minor FROM Refund ORDER BY id')],
            'events_for_attempted_refund':db.execute("SELECT COUNT(*) FROM EventLog WHERE Refund_id='REF-2026-000002'").fetchone()[0]}
    db.close(); return result

# Expected decisions and effects are authored from the documented rules and fixture facts.
TRUTH = {
 'quantity':('NO_REMAINING_QUANTITY','PARTIAL_REMAINING_QUANTITY',0,1),
 'excess':('REFUND_SUCCESS_GUARD','REFUND_SUCCEEDED',0,100),
 'inventory':('MOVEMENT_REQUIRES_ACCEPTED_DECISION','RESTOCK_POSTED',0,2),
 'late':('WINDOW_EXPIRED','ELIGIBLE',0,2),
 'duplicate':('DUPLICATE_PAYMENT_KEY','REFUND_SUCCEEDED',0,100),
}
RULES={'quantity':'cumulative return reservation','excess':'remaining refund entitlement','inventory':'inspection before restock','late':'inclusive return window','duplicate':'one successful payment per key'}
PRECONDITIONS={
 'quantity':{'purchase_units':2,'reserved_units_negative':2,'reserved_units_control':1,'requested_units':2},
 'excess':{'purchase_paid_minor':200,'obligation_minor':200,'previous_success_minor':100,'attempt_minor_negative':200,'attempt_minor_control':100},
 'inventory':{'received_units':2,'negative_inspection':'absent','control_inspection':'FINALIZED SELLABLE','movement_units':2},
 'late':{'delivery_date_local':'2026-10-01','inclusive_deadline_local':'2026-10-31','negative_request_date_local':'2026-11-01','control_request_date_local':'2026-10-31','override':None},
 'duplicate':{'obligation_minor':200,'negative_prior_payment':'SUCCEEDED 100','control_prior_payment':'FAILED 0','retry_minor':100,'payment_key':'logical-payment'},
}

def evaluate(truth, observations):
    rows=[]
    for expected in truth:
        o=next(x for x in observations if x['scenario_id']==expected['scenario_id'])
        delta={k:o['final'][k]-o['initial'][k] for k in ('paid_minor','restocked_units','reserved_units')}
        checks={'decision':o['observed_decision']==expected['expected_decision'], 'reason':o['observed_reason_code']==expected['expected_reason_code'], 'effects':delta==expected['expected_effects'], 'sqlite_integrity':o['integrity_check']=='ok','foreign_keys':not o['foreign_key_violations']}
        if expected['scenario_id'] in ('excess_negative','duplicate_negative'):
            checks['transition_rollback']=o['final']['events']==o['initial']['events'] and o['events_for_attempted_refund']==1 and any(r['id']=='REF-2026-000002' and r['state']=='REQUESTED' and r['paid_minor']==0 for r in o['refund_states'])
        if expected['scenario_id']=='inventory_negative': checks['movement_rollback']=o['final']['events']==o['initial']['events']
        rows.append({'scenario_id':o['scenario_id'],'checks':checks,'enforcement_pass':all(checks.values()),'observed_effects':delta})
    return rows

def run(destination):
    dest=Path(destination); dest.mkdir(parents=True,exist_ok=False)
    observations=[]; truth=[]
    for case,(bad,good,_,amount) in TRUTH.items():
        for control in (False,True):
            sid=case+('_control' if control else '_negative')
            observations.append(run_one(dest/(sid+'.db'),case,control))
            effect={'paid_minor':0,'restocked_units':0,'reserved_units':0}
            if control: effect['paid_minor' if case in ('excess','duplicate') else 'restocked_units' if case=='inventory' else 'reserved_units']=amount
            truth.append({'scenario_id':sid,'category':case,'rule_id':RULES[case], 'fixture':sid+'.db','fixture_entities':['ORD-2026-000001','ORL-2026-000001','RMA-2026-000001'], 'preconditions':PRECONDITIONS[case], 'attempted_operation':{'quantity':'authorize second request for two units','excess':'post successful refund against remaining entitlement','inventory':'post restock movement','late':'authorize request at configured date','duplicate':'post another success with the same payment key'}[case], 'expected_decision':'ALLOWED' if control else 'BLOCKED','expected_reason_code':good if control else bad,'expected_effects':effect})
    results=evaluate(truth,observations)
    for name,data in [('ground_truth.json',truth),('observations.json',observations),('scenario_results.json',results)]:
        (dest/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    if not all(x['enforcement_pass'] for x in results): raise RuntimeError('Scenario evaluation failed')
    return results

if __name__=='__main__':
    results=run(sys.argv[1]); print(json.dumps(results,indent=2)); print('All checks passed:',all(x['enforcement_pass'] for x in results))
