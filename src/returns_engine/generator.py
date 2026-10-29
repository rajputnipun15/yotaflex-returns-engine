"""One dependency-aware baseline pipeline for starter, custom and full scales."""

from bisect import bisect_right
from datetime import timedelta
from itertools import accumulate
import json
import random

from .config import validate_config
from .events import record_event
from .ids import allocate_id, return_line_id
from .money import basis_points, allocate_proportional, unit_paid
from .policy import parse_time, authorize_request
from .schema import transaction, quote

GENERATOR_VERSION = "0.3.0"


def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def choose(rng, weights):
    keys=sorted(weights)
    cumulative=list(accumulate(weights[k] for k in keys))
    return keys[bisect_right(cumulative,rng.randrange(cumulative[-1]))]


class BaselineGenerator:
    def __init__(self, conn, config):
        validate_config(config)
        self.db=conn
        self.c=config
        self.rng=random.Random(config["seed"])
        self.as_of=parse_time(config["as_of"])
        self.catalog=[]
        self.customer_profiles=[]
        self.catalog_by_category={}
        self.order_ids=[]

    def create(self, table, values, at, *, correlation=None, reason="SYNTHETIC_CREATED"):
        identifier=allocate_id(self.db,table)
        self.insert(table,{"id":identifier,**values},at,correlation=correlation,reason=reason)
        return identifier

    def insert(self, table, values, at, *, correlation=None, reason="SYNTHETIC_CREATED"):
        columns=",".join(quote(k) for k in values)
        self.db.execute(f'INSERT INTO {quote(table)}({columns}) VALUES('+",".join("?" for _ in values)+")",tuple(values.values()))
        record_event(self.db,table,values["id"],event_type="CREATED",occurred_at=stamp(at),reason_code=reason,correlation_id=correlation or values["id"])

    def transition(self, table, identifier, state, at, correlation, reason="WORKFLOW_PREREQUISITES_MET", **changes):
        record_event(self.db,table,identifier,event_type="STATE_CHANGED",new_state=state,
            occurred_at=stamp(at),reason_code=reason,correlation_id=correlation,changes=changes)

    def run(self, progress=None):
        counts=self.c["counts"]
        if any(self.db.execute(f'SELECT 1 FROM {quote(t)} LIMIT 1').fetchone() for t in ("Customer","Order","ReturnRequest")):
            raise ValueError("Generation requires a fresh empty business database")
        request_sizes=[1]*counts["requests"]
        shuffled=list(range(counts["requests"]))
        self.rng.shuffle(shuffled)
        for i in range(counts["return_lines"]-counts["requests"]):
            request_sizes[shuffled[i % len(shuffled)]]+=1
        request_orders=[(0 if i<2 else (i-1)%counts["orders"]) if self.c["coverage_strata"] and i<12 else self.rng.randrange(counts["orders"]) for i in range(counts["requests"])]
        required={}
        for order,size in zip(request_orders,request_sizes): required[order]=max(required.get(order,0),size)
        with transaction(self.db):
            self.masters()
            if progress: progress("masters created")
            self.orders(required)
            if progress: progress("orders and purchased lines created")
            last_request={}
            work=[]
            forced=["FIRST_PARTIAL","REPEAT_FULL","LATE","EXCLUDED","EXCHANGE","PENDING_REQUEST","PENDING_SHIPMENT","MISSING","PENDING_INSPECTION","PENDING_REFUND","PENDING_MOVEMENT","DAMAGE"]
            for i,(order_index,size) in enumerate(zip(request_orders,request_sizes)):
                mode=forced[i] if self.c["coverage_strata"] and i<len(forced) else choose(self.rng,self.c["request_modes"])
                work.append(self.request(order_index,size,mode,last_request))
            if progress: progress("all return request/line masters created before authorization")
            for i,(request,requested,resolution,mode) in enumerate(work):
                if mode!="PENDING_REQUEST":
                    header,_=authorize_request(self.db,request,self.c)
                    if header is not None: self.fulfill(request,header,requested,resolution,mode)
                if progress and (i+1)%1000==0: progress(f"processed {i+1} return requests")
            if progress: progress("dependent baseline transactions and events created")
        return {"catalog":self.catalog,"customers":self.customer_profiles}

    def masters(self):
        n=max(1,self.c["counts"]["orders"]//self.c["customers_per_order_divisor"])
        segments=sorted(self.c["segments"])
        for i in range(n):
            segment=self.rng.choice(segments)
            region=self.rng.choice(self.c["regions"])
            created=self.as_of-timedelta(days=365+self.rng.randrange(60))
            identifier=self.create("Customer",{"synthetic_name":f"Synthetic {region} {segment} customer {i+1:06d}","state":"ACTIVE","created_at":stamp(created)},created)
            self.customer_profiles.append({"customer_id":identifier,"region":region,"segment":segment})
        self.customer_cumulative=list(accumulate(self.c["segments"][p["segment"]] for p in self.customer_profiles))
        category_names=sorted(self.c["categories"])
        for i in range(self.c["catalog_size"]):
            category=category_names[i%len(category_names)]
            policy=self.c["categories"][category]
            price=self.rng.randint(policy["min_price_minor"],policy["max_price_minor"])
            name=f"Synthetic {category.lower().replace('_',' ')} item {i+1:03d}"
            identifier=self.create("Product",{"category":category,"description":name},self.as_of-timedelta(days=500))
            item={"product_id":identifier,"name":name,"category":category,"unit_price_minor":price,
                "returnable":policy["returnable"],"window_days":policy["window_days"]}
            self.catalog.append(item)
            self.catalog_by_category.setdefault(category,[]).append(item)
        self.policy=self.create("ReturnPolicy",{"window_days":self.c["window_days"],
            "excluded_categories_json":json.dumps(sorted(k for k,v in self.c["categories"].items() if not v["returnable"]),separators=(",",":")),
            "fee_bps":self.c["fee_bps"],"effective_from":stamp(self.as_of-timedelta(days=730)),"effective_to":None},self.as_of-timedelta(days=730))

    def orders(self, required):
        maximum_window=max(p["window_days"] for p in self.c["categories"].values())
        returnable=sorted(k for k,p in self.c["categories"].items() if p["returnable"])
        excluded=sorted(k for k,p in self.c["categories"].items() if not p["returnable"])
        for i in range(self.c["counts"]["orders"]):
            customer=self.customer_profiles[bisect_right(self.customer_cumulative,self.rng.randrange(self.customer_cumulative[-1]))]["customer_id"]
            placed=self.as_of-timedelta(days=maximum_window+45+self.rng.randrange(120),hours=self.rng.randrange(24))
            delivered=placed+timedelta(days=self.rng.randint(2,7))
            identifier=self.create("Order",{"customer_id":customer,"currency":self.c["currency"],"placed_at":stamp(placed),
                "delivered_at":None,"shipping_paid_minor":self.rng.choice([0,0,0,499,799]),"state":"PLACED"},placed)
            self.order_ids.append(identifier)
            self.transition("Order",identifier,"FULFILLED",placed+timedelta(days=1),identifier)
            self.transition("Order",identifier,"DELIVERED",delivered,identifier,delivered_at=stamp(delivered))
        # All Order parents now exist. Stream one order and its purchased lines.
        for i,order in enumerate(self.db.execute('SELECT * FROM "Order" ORDER BY id')):
            count=max(required.get(i,1),int(choose(self.rng,self.c["order_line_weights"])))
            lines=[]
            for j in range(count):
                category=choose(self.rng,{k:v["weight"] for k,v in self.c["categories"].items()})
                if self.c["coverage_strata"] and 0<i<11 and i!=2:
                    category=choose(self.rng,{k:self.c["categories"][k]["weight"] for k in returnable})
                if self.c["coverage_strata"] and i==0: category=returnable[0]
                if self.c["coverage_strata"] and i==2 and excluded: category=excluded[0]  # stratified input, not a random rejection
                product=self.rng.choice(self.catalog_by_category[category])
                quantity=int(choose(self.rng,self.c["quantity_weights"]))
                if self.c["coverage_strata"] and i==0: quantity=max(quantity,max(int(x) for x in self.c["quantity_weights"]))
                gross=quantity*product["unit_price_minor"]
                discount=basis_points(gross,self.rng.choice(self.c["line_discount_bps"]))
                lines.append({"order_id":order["id"],"product_id":product["product_id"],"quantity":quantity,
                    "unit_price_minor":product["unit_price_minor"],"line_discount_minor":discount})
            net=[l["quantity"]*l["unit_price_minor"]-l["line_discount_minor"] for l in lines]
            order_discount=basis_points(sum(net),self.rng.choice(self.c["order_discount_bps"]))
            allocations=allocate_proportional(order_discount,net)
            for line,allocated in zip(lines,allocations):
                taxable=line["quantity"]*line["unit_price_minor"]-line["line_discount_minor"]-allocated
                tax=basis_points(taxable,self.c["tax_bps"])
                self.create("OrderLine",{**line,"order_discount_allocated_minor":allocated,"tax_minor":tax,"paid_minor":taxable+tax},parse_time(order["placed_at"]),correlation=order["id"])

    def request(self, order_index, size, mode, last_request):
        # Parent IDs are read from existing rows, never guessed/generated separately.
        order=self.db.execute('SELECT * FROM "Order" WHERE id=?',(self.order_ids[order_index],)).fetchone()
        available=list(self.db.execute('SELECT o.*,p.category FROM OrderLine o JOIN Product p ON p.id=o.product_id WHERE order_id=? ORDER BY o.id',(order["id"],)))
        selected=available[:size] if mode in ("FIRST_PARTIAL","REPEAT_FULL") else sorted(self.rng.sample(available,size),key=lambda r:r["id"])
        window=min(self.c["categories"][l["category"]]["window_days"] for l in selected)
        days=window+self.rng.randint(1,10) if mode=="LATE" else self.rng.randint(1,max(1,window))
        if mode in ("FIRST_PARTIAL","REPEAT_FULL"): days=min(5,window)
        requested=parse_time(order["delivered_at"])+timedelta(days=days)
        if order["id"] in last_request: requested=max(requested,last_request[order["id"]]+timedelta(hours=1))
        last_request[order["id"]]=requested
        resolution="EXCHANGE" if mode=="EXCHANGE" or (mode not in ("FIRST_PARTIAL","REPEAT_FULL") and self.rng.randrange(100)<self.c["exchange_percent"]) else "REFUND"
        request=self.create("ReturnRequest",{"order_id":order["id"],"policy_id":self.policy,"requested_at":stamp(requested),
            "resolution":resolution,"override_reason":None,"state":"REQUESTED"},requested)
        for sequence,line in enumerate(selected,1):
            quantity=1 if mode=="FIRST_PARTIAL" else (line["quantity"] if mode=="REPEAT_FULL" else self.rng.randint(1,line["quantity"]))
            reason="DAMAGE" if mode=="DAMAGE" else choose(self.rng,self.c["return_reason_weights"])
            self.insert("ReturnLine",{"id":return_line_id(request,sequence),"request_id":request,"order_line_id":line["id"],
                "line_sequence":sequence,"requested_quantity":quantity,"reason_code":reason,"state":"REQUESTED"},requested,correlation=request)
        return request,requested,resolution,mode

    def fulfill(self, request, header, at, resolution, mode):
        if mode=="PENDING_SHIPMENT": return
        allocations=list(self.db.execute('''SELECT a.*,l.order_line_id,l.reason_code FROM AuthorizationLine a
            JOIN ReturnLine l ON l.id=a.return_line_id WHERE authorization_id=? ORDER BY a.id''',(header,)))
        split=self.rng.randrange(100)<self.c["split_shipment_percent"] and any(a["approved_quantity"]>1 for a in allocations)
        pieces=[]
        for a in allocations:
            quantities=[1,a["approved_quantity"]-1] if split else [a["approved_quantity"]]
            for part,quantity in enumerate(quantities):
                if quantity: pieces.append((part,a,quantity))
        shipment_lines=[]
        for part in sorted({p for p,_,_ in pieces}):
            created=at+timedelta(days=1)
            shipment=self.create("ReturnShipment",{"created_at":stamp(created),"dispatched_at":None,"delivered_at":None,"state":"CREATED"},created,correlation=request)
            self.transition("ReturnShipment",shipment,"DISPATCHED",at+timedelta(days=2),request,dispatched_at=stamp(at+timedelta(days=2)))
            if mode=="MISSING": self.transition("ReturnShipment",shipment,"MISSING",at+timedelta(days=5),request,reason="NO_RECEIPT_BY_SIMULATED_DEADLINE")
            else: self.transition("ReturnShipment",shipment,"DELIVERED",at+timedelta(days=4+part),request,delivered_at=stamp(at+timedelta(days=4+part)))
            for piece,a,quantity in pieces:
                if piece!=part: continue
                sid=self.create("ShipmentLine",{"shipment_id":shipment,"authorization_line_id":a["id"],"shipped_quantity":quantity,
                    "received_quantity":0},at+timedelta(days=2),correlation=request)
                if mode!="MISSING":
                    # Atomic baseline transaction; receipt is an explicit observation,
                    # recorded before any inspection freezes the quantity evidence.
                    self.db.execute("UPDATE ShipmentLine SET received_quantity=? WHERE id=?",(quantity,sid))
                    record_event(self.db,"ShipmentLine",sid,event_type="OBSERVED",occurred_at=stamp(at+timedelta(days=4+part)),reason_code="RECEIVED_QUANTITY_RECORDED",correlation_id=request)
                shipment_lines.append((part,sid,a,quantity))
        self.transition("ReturnRequest",request,"IN_TRANSIT",at+timedelta(days=2),request)
        for a in allocations: self.transition("ReturnLine",a["return_line_id"],"SHIPPED",at+timedelta(days=2),request)
        if mode=="MISSING": return
        self.transition("ReturnRequest",request,"RECEIVED",at+timedelta(days=5),request)
        for a in allocations: self.transition("ReturnLine",a["return_line_id"],"RECEIVED",at+timedelta(days=5),request)
        if mode=="PENDING_INSPECTION": return
        inspections=[]
        offsets={}
        for part,sid,a,quantity in shipment_lines:
            inspected=at+timedelta(days=6+part)
            condition=choose(self.rng,self.c["damage_condition_weights"]) if a["reason_code"]=="DAMAGE" else choose(self.rng,self.c["ordinary_condition_weights"])
            inspection=self.create("Inspection",{"shipment_line_id":sid,"inspected_quantity":quantity,"condition":condition,
                "inspected_at":stamp(inspected),"state":"RECORDED"},inspected,correlation=request)
            self.transition("Inspection",inspection,"FINALIZED",inspected,request)
            original=self.db.execute("SELECT * FROM OrderLine WHERE id=?",(a["order_line_id"],)).fetchone()
            if a["id"] not in offsets:
                offsets[a["id"]]=self.db.execute('''SELECT COALESCE(SUM(b.approved_quantity),0) FROM AuthorizationLine b
                    JOIN ReturnLine l ON l.id=b.return_line_id JOIN ReturnAuthorization h ON h.id=b.authorization_id
                    WHERE l.order_line_id=? AND b.rowid<(SELECT rowid FROM AuthorizationLine WHERE id=?)
                    AND (h.state IN ('ISSUED','CONSUMED') OR EXISTS(SELECT 1 FROM ShipmentLine s WHERE s.authorization_line_id=b.id))''',(original["id"],a["id"])).fetchone()[0]
            start=offsets[a["id"]]
            gross_entitlement=sum(unit_paid(original)[start:start+quantity])
            if start+quantity>original["quantity"]: raise ValueError("Reserved unit positions exceed purchased quantity")
            offsets[a["id"]]+=quantity
            inspections.append((inspection,a,quantity,condition,gross_entitlement))
        for a in allocations: self.transition("ReturnLine",a["return_line_id"],"INSPECTED",at+timedelta(days=8),request)
        self.transition("ReturnRequest",request,"INSPECTED",at+timedelta(days=8),request)
        self.transition("ReturnAuthorization",header,"CONSUMED",at+timedelta(days=8),request)
        for inspection,a,quantity,condition,gross in inspections:
            if resolution=="REFUND":
                fee=basis_points(gross,self.c["fee_bps"])
                obligation=self.create("RefundObligation",{"return_line_id":a["return_line_id"],"inspection_id":inspection,
                    "entitlement_minor":gross-fee,"fee_minor":fee},at+timedelta(days=9),correlation=request)
                if gross-fee>0:
                    self.payment(obligation,gross-fee,at+timedelta(days=9),request,mode)
            else:
                record_event(self.db,"ReturnLine",a["return_line_id"],event_type="OBSERVED",occurred_at=stamp(at+timedelta(days=9)),reason_code="EXCHANGE_PENDING_REPLACEMENT",correlation_id=request)
            route={"SELLABLE":"RESTOCK","REPAIRABLE":"REFURBISH","UNSAFE":"QUARANTINE","IRREPARABLE":"SCRAP"}[condition]
            disposition=self.create("InventoryDisposition",{"return_line_id":a["return_line_id"],"inspection_id":inspection,
                "action":route,"quantity":quantity,"decided_at":stamp(at+timedelta(days=9)),"reason_code":"INSPECTION_ROUTE","state":"PROPOSED"},at+timedelta(days=9),correlation=request)
            self.transition("InventoryDisposition",disposition,"ACCEPTED",at+timedelta(days=9),request)
            if mode!="PENDING_MOVEMENT": self.create("InventoryMovement",{"disposition_id":disposition,"quantity":quantity,"moved_at":stamp(at+timedelta(days=10))},at+timedelta(days=10),correlation=request)
        if resolution=="REFUND" and mode not in ("PENDING_REFUND","PENDING_MOVEMENT"):
            for a in allocations: self.transition("ReturnLine",a["return_line_id"],"SETTLED",at+timedelta(days=11),request)
            self.transition("ReturnRequest",request,"CLOSED",at+timedelta(days=12),request)

    def payment(self, obligation, amount, at, request, mode):
        attempts=2 if mode!="PENDING_REFUND" and self.rng.randrange(100)<self.c["failed_payment_percent"] else 1
        for index in range(attempts):
            attempted=at+timedelta(hours=index)
            remaining=amount-self.db.execute("SELECT COALESCE(SUM(paid_minor),0) FROM Refund WHERE obligation_id=?",(obligation,)).fetchone()[0]
            refund=self.create("Refund",{"obligation_id":obligation,"payment_key":"PAY-"+obligation,"requested_minor":remaining,
                "paid_minor":0,"attempted_at":stamp(attempted),"reason_code":None,"state":"REQUESTED"},attempted,correlation=request)
            if mode=="PENDING_REFUND": return
            state="FAILED" if attempts==2 and index==0 else "SUCCEEDED"
            self.transition("Refund",refund,state,attempted,request,reason="PAYMENT_PROVIDER_FAILURE" if state=="FAILED" else "PAYOUT_CONFIRMED",
                paid_minor=0 if state=="FAILED" else remaining,reason_code="PROVIDER_FAILURE" if state=="FAILED" else "PAID")
