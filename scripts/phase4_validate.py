"""Independently inspect persisted Phase 4 fixtures and compare repeat runs."""
import hashlib
import json
import sys
from pathlib import Path
from returns_engine.model import TARGETS
from returns_engine.schema import connect

def verify(folder):
    folder=Path(folder)
    truth=json.loads((folder/'ground_truth.json').read_text(encoding='utf-8'))
    observations=json.loads((folder/'observations.json').read_text(encoding='utf-8'))
    results=json.loads((folder/'scenario_results.json').read_text(encoding='utf-8'))
    checks=[]; digests={}
    for t in truth:
        sid=t['scenario_id']; db=connect(folder/t['fixture'])
        o=next(x for x in observations if x['scenario_id']==sid)
        events=list(db.execute('SELECT * FROM EventLog ORDER BY id'))
        histories={}; times={}; valid=True
        for e in events:
            target=next((x for x in TARGETS if e[x+'_id'] is not None),None)
            key=(target,e[target+'_id'])
            if key in times and e['occurred_at'] < times[key]: valid=False
            times[key]=e['occurred_at']
            if e['event_type']=='CREATED':
                if key in histories: valid=False
                histories[key]=e['new_state']
            elif e['event_type']=='STATE_CHANGED':
                if key not in histories or histories[key]!=e['previous_state']: valid=False
                histories[key]=e['new_state']
        for (table,ident),state in histories.items():
            row=db.execute('SELECT * FROM "'+table+'" WHERE id=?',(ident,)).fetchone()
            if row is None or ('state' in row.keys() and row['state']!=state): valid=False
        actual={'paid_minor':db.execute('SELECT COALESCE(SUM(paid_minor),0) FROM Refund').fetchone()[0],
                'restocked_units':db.execute("SELECT COALESCE(SUM(m.quantity),0) FROM InventoryMovement m JOIN InventoryDisposition d ON d.id=m.disposition_id WHERE d.action='RESTOCK'").fetchone()[0],
                'reserved_units':db.execute("SELECT COALESCE(SUM(a.approved_quantity),0) FROM AuthorizationLine a JOIN ReturnAuthorization h ON h.id=a.authorization_id WHERE h.state IN ('ISSUED','CONSUMED')").fetchone()[0]}
        refs=all(db.execute('SELECT 1 FROM "'+table+'" WHERE id=?',(ident,)).fetchone() for table,ident in zip(('Order','OrderLine','ReturnRequest'),t['fixture_entities']))
        negative=sid.endswith('_negative')
        if negative and t['category']=='quantity': pre=o['initial']['reserved_units']==2
        elif negative and t['category']=='excess': pre=o['initial']['paid_minor']==100 and o['attempted_operation']['amount_minor']==200
        elif negative and t['category']=='inventory': pre=db.execute('SELECT COUNT(*) FROM Inspection').fetchone()[0]==0
        elif negative and t['category']=='late': pre=db.execute('SELECT requested_at FROM ReturnRequest').fetchone()[0]=='2026-11-01T00:00:00Z'
        elif negative and t['category']=='duplicate': pre=o['initial']['paid_minor']==100 and db.execute("SELECT COUNT(*) FROM Refund WHERE payment_key='logical-payment' AND state='SUCCEEDED'").fetchone()[0]==1
        else: pre=True
        consistent=all(actual[k]==o['final'][k] for k in actual)
        delta={k:actual[k]-o['initial'][k] for k in actual}
        checks.append({'scenario_id':sid,'references':bool(refs),'preconditions':pre,'event_history':valid,'observed_balances_match_database':consistent,'expected_effects':delta==t['expected_effects'], 'decision_and_reason':(o['observed_decision'],o['observed_reason_code'])==(t['expected_decision'],t['expected_reason_code']), 'sqlite_integrity':db.execute('PRAGMA integrity_check').fetchone()[0]=='ok','foreign_keys':not list(db.execute('PRAGMA foreign_key_check')),'evaluation':next(r for r in results if r['scenario_id']==sid)['enforcement_pass']})
        dump='\n'.join(db.iterdump()).encode('utf-8'); digests[sid]=hashlib.sha256(dump).hexdigest(); db.close()
    coverage=sorted(set(x['category'] for x in truth))==['duplicate','excess','inventory','late','quantity'] and len(truth)==10 and len({x['scenario_id'] for x in truth})==10
    return {'coverage':coverage,'checks':checks,'logical_database_sha256':digests,'pass':coverage and all(all(v for k,v in c.items() if k!='scenario_id') for c in checks)}

if __name__=='__main__':
    a=verify(sys.argv[1]); b=verify(sys.argv[2]);
    files=['ground_truth.json','observations.json','scenario_results.json']
    match={f:(Path(sys.argv[1])/f).read_bytes()==(Path(sys.argv[2])/f).read_bytes() for f in files}
    report={'first':a,'repeat':b,'json_matches':match,'logical_database_matches':a['logical_database_sha256']==b['logical_database_sha256']}
    print(json.dumps(report,indent=2,sort_keys=True))
    sys.exit(0 if a['pass'] and b['pass'] and all(match.values()) and report['logical_database_matches'] else 1)
