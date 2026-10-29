PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS SchemaVersion (version INTEGER NOT NULL PRIMARY KEY CHECK(version=2)) STRICT;
CREATE TABLE IF NOT EXISTS IdSequence (entity TEXT NOT NULL PRIMARY KEY, last_value INTEGER NOT NULL CHECK(last_value BETWEEN 1 AND 999999)) STRICT;
CREATE TABLE IF NOT EXISTS "Customer" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'CUS-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"synthetic_name" TEXT NOT NULL CHECK("synthetic_name" IS NULL OR length(trim("synthetic_name"))>0),
"state" TEXT NOT NULL CHECK("state" IS NULL OR length(trim("state"))>0) CHECK("state" IN ('ACTIVE','INACTIVE')),
"created_at" TEXT NOT NULL CHECK("created_at" IS NULL OR length(trim("created_at"))>0) CHECK(length("created_at")=20 AND "created_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z')) STRICT;
CREATE TRIGGER IF NOT EXISTS "Customer_immutable_id" BEFORE UPDATE OF id ON "Customer"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "Product" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'PRD-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"category" TEXT NOT NULL CHECK("category" IS NULL OR length(trim("category"))>0),
"description" TEXT NOT NULL CHECK("description" IS NULL OR length(trim("description"))>0)) STRICT;
CREATE TRIGGER IF NOT EXISTS "Product_immutable_id" BEFORE UPDATE OF id ON "Product"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "ReturnPolicy" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'POL-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"window_days" INTEGER NOT NULL CHECK("window_days" >= 0),
"excluded_categories_json" TEXT NOT NULL CHECK("excluded_categories_json" IS NULL OR length(trim("excluded_categories_json"))>0) CHECK(json_valid(excluded_categories_json) AND json_type(excluded_categories_json)='array'),
"fee_bps" INTEGER NOT NULL CHECK("fee_bps" >= 0),
"effective_from" TEXT NOT NULL CHECK("effective_from" IS NULL OR length(trim("effective_from"))>0) CHECK(length("effective_from")=20 AND "effective_from" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
"effective_to" TEXT CHECK("effective_to" IS NULL OR length(trim("effective_to"))>0) CHECK(length("effective_to")=20 AND "effective_to" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
CHECK(fee_bps<=10000),
CHECK(effective_to IS NULL OR effective_to>effective_from)) STRICT;
CREATE TRIGGER IF NOT EXISTS "ReturnPolicy_immutable_id" BEFORE UPDATE OF id ON "ReturnPolicy"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "Order" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'ORD-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"customer_id" TEXT NOT NULL REFERENCES "Customer"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("customer_id" IS NULL OR length(trim("customer_id"))>0),
"currency" TEXT NOT NULL CHECK("currency" IS NULL OR length(trim("currency"))>0) CHECK(length(currency)=3 AND currency NOT GLOB '*[^A-Z]*'),
"placed_at" TEXT NOT NULL CHECK("placed_at" IS NULL OR length(trim("placed_at"))>0) CHECK(length("placed_at")=20 AND "placed_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
"delivered_at" TEXT CHECK("delivered_at" IS NULL OR length(trim("delivered_at"))>0) CHECK(length("delivered_at")=20 AND "delivered_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
"shipping_paid_minor" INTEGER NOT NULL CHECK("shipping_paid_minor" >= 0),
"state" TEXT NOT NULL CHECK("state" IS NULL OR length(trim("state"))>0) CHECK("state" IN ('PLACED','FULFILLED','DELIVERED')),
CHECK(delivered_at IS NULL OR delivered_at>=placed_at),
CHECK(state<>'DELIVERED' OR delivered_at IS NOT NULL)) STRICT;
CREATE INDEX IF NOT EXISTS "ix_Order_customer_id" ON "Order"("customer_id");
CREATE TRIGGER IF NOT EXISTS "Order_immutable_id" BEFORE UPDATE OF id ON "Order"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "OrderLine" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'ORL-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"order_id" TEXT NOT NULL REFERENCES "Order"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("order_id" IS NULL OR length(trim("order_id"))>0),
"product_id" TEXT NOT NULL REFERENCES "Product"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("product_id" IS NULL OR length(trim("product_id"))>0),
"quantity" INTEGER NOT NULL CHECK("quantity" >= 1),
"unit_price_minor" INTEGER NOT NULL CHECK("unit_price_minor" >= 0),
"line_discount_minor" INTEGER NOT NULL CHECK("line_discount_minor" >= 0),
"order_discount_allocated_minor" INTEGER NOT NULL CHECK("order_discount_allocated_minor" >= 0),
"tax_minor" INTEGER NOT NULL CHECK("tax_minor" >= 0),
"paid_minor" INTEGER NOT NULL CHECK("paid_minor" >= 0),
CHECK(line_discount_minor+order_discount_allocated_minor<=quantity*unit_price_minor),
CHECK(paid_minor=quantity*unit_price_minor-line_discount_minor-order_discount_allocated_minor+tax_minor),
CHECK(typeof(quantity*unit_price_minor)='integer')) STRICT;
CREATE INDEX IF NOT EXISTS "ix_OrderLine_order_id" ON "OrderLine"("order_id");
CREATE INDEX IF NOT EXISTS "ix_OrderLine_product_id" ON "OrderLine"("product_id");
CREATE TRIGGER IF NOT EXISTS "OrderLine_immutable_id" BEFORE UPDATE OF id ON "OrderLine"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "ReturnRequest" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'RMA-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"order_id" TEXT NOT NULL REFERENCES "Order"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("order_id" IS NULL OR length(trim("order_id"))>0),
"policy_id" TEXT NOT NULL REFERENCES "ReturnPolicy"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("policy_id" IS NULL OR length(trim("policy_id"))>0),
"requested_at" TEXT NOT NULL CHECK("requested_at" IS NULL OR length(trim("requested_at"))>0) CHECK(length("requested_at")=20 AND "requested_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
"resolution" TEXT NOT NULL CHECK("resolution" IS NULL OR length(trim("resolution"))>0) CHECK("resolution" IN ('REFUND','EXCHANGE')),
"override_reason" TEXT CHECK("override_reason" IS NULL OR length(trim("override_reason"))>0),
"state" TEXT NOT NULL CHECK("state" IS NULL OR length(trim("state"))>0) CHECK("state" IN ('REQUESTED','APPROVED','PARTIALLY_APPROVED','REJECTED','IN_TRANSIT','RECEIVED','INSPECTED','CLOSED','CANCELLED'))) STRICT;
CREATE INDEX IF NOT EXISTS "ix_ReturnRequest_order_id" ON "ReturnRequest"("order_id");
CREATE INDEX IF NOT EXISTS "ix_ReturnRequest_policy_id" ON "ReturnRequest"("policy_id");
CREATE TRIGGER IF NOT EXISTS "ReturnRequest_immutable_id" BEFORE UPDATE OF id ON "ReturnRequest"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "ReturnLine" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0),
"request_id" TEXT NOT NULL REFERENCES "ReturnRequest"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("request_id" IS NULL OR length(trim("request_id"))>0),
"order_line_id" TEXT NOT NULL REFERENCES "OrderLine"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("order_line_id" IS NULL OR length(trim("order_line_id"))>0),
"line_sequence" INTEGER NOT NULL CHECK("line_sequence" >= 1),
"requested_quantity" INTEGER NOT NULL CHECK("requested_quantity" >= 1),
"reason_code" TEXT NOT NULL CHECK("reason_code" IS NULL OR length(trim("reason_code"))>0),
"state" TEXT NOT NULL CHECK("state" IS NULL OR length(trim("state"))>0) CHECK("state" IN ('REQUESTED','APPROVED','PARTIALLY_APPROVED','REJECTED','SHIPPED','RECEIVED','INSPECTED','SETTLED','CANCELLED')),
UNIQUE(request_id,line_sequence),
CHECK(line_sequence<=99),
CHECK(id='RMAL-'||request_id||'-'||printf('%02d',line_sequence))) STRICT;
CREATE INDEX IF NOT EXISTS "ix_ReturnLine_request_id" ON "ReturnLine"("request_id");
CREATE INDEX IF NOT EXISTS "ix_ReturnLine_order_line_id" ON "ReturnLine"("order_line_id");
CREATE TRIGGER IF NOT EXISTS "ReturnLine_immutable_id" BEFORE UPDATE OF id ON "ReturnLine"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "ReturnAuthorization" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'RAU-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"request_id" TEXT NOT NULL REFERENCES "ReturnRequest"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("request_id" IS NULL OR length(trim("request_id"))>0),
"issued_at" TEXT NOT NULL CHECK("issued_at" IS NULL OR length(trim("issued_at"))>0) CHECK(length("issued_at")=20 AND "issued_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
"state" TEXT NOT NULL CHECK("state" IS NULL OR length(trim("state"))>0) CHECK("state" IN ('ISSUED','SUPERSEDED','CANCELLED','CONSUMED'))) STRICT;
CREATE INDEX IF NOT EXISTS "ix_ReturnAuthorization_request_id" ON "ReturnAuthorization"("request_id");
CREATE TRIGGER IF NOT EXISTS "ReturnAuthorization_immutable_id" BEFORE UPDATE OF id ON "ReturnAuthorization"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "AuthorizationLine" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'RAL-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"authorization_id" TEXT NOT NULL REFERENCES "ReturnAuthorization"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("authorization_id" IS NULL OR length(trim("authorization_id"))>0),
"return_line_id" TEXT NOT NULL REFERENCES "ReturnLine"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("return_line_id" IS NULL OR length(trim("return_line_id"))>0),
"approved_quantity" INTEGER NOT NULL CHECK("approved_quantity" >= 1),
UNIQUE(authorization_id,return_line_id)) STRICT;
CREATE INDEX IF NOT EXISTS "ix_AuthorizationLine_authorization_id" ON "AuthorizationLine"("authorization_id");
CREATE INDEX IF NOT EXISTS "ix_AuthorizationLine_return_line_id" ON "AuthorizationLine"("return_line_id");
CREATE TRIGGER IF NOT EXISTS "AuthorizationLine_immutable_id" BEFORE UPDATE OF id ON "AuthorizationLine"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "ReturnShipment" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'RTS-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"created_at" TEXT NOT NULL CHECK("created_at" IS NULL OR length(trim("created_at"))>0) CHECK(length("created_at")=20 AND "created_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
"dispatched_at" TEXT CHECK("dispatched_at" IS NULL OR length(trim("dispatched_at"))>0) CHECK(length("dispatched_at")=20 AND "dispatched_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
"delivered_at" TEXT CHECK("delivered_at" IS NULL OR length(trim("delivered_at"))>0) CHECK(length("delivered_at")=20 AND "delivered_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
"state" TEXT NOT NULL CHECK("state" IS NULL OR length(trim("state"))>0) CHECK("state" IN ('CREATED','DISPATCHED','DELIVERED','MISSING')),
CHECK(dispatched_at IS NULL OR dispatched_at>=created_at),
CHECK(delivered_at IS NULL OR (dispatched_at IS NOT NULL AND delivered_at>=dispatched_at)),
CHECK(state NOT IN ('DISPATCHED','MISSING','DELIVERED') OR dispatched_at IS NOT NULL),
CHECK(state<>'DELIVERED' OR delivered_at IS NOT NULL),
CHECK(state<>'MISSING' OR delivered_at IS NULL)) STRICT;
CREATE TRIGGER IF NOT EXISTS "ReturnShipment_immutable_id" BEFORE UPDATE OF id ON "ReturnShipment"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "ShipmentLine" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'SHL-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"shipment_id" TEXT NOT NULL REFERENCES "ReturnShipment"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("shipment_id" IS NULL OR length(trim("shipment_id"))>0),
"authorization_line_id" TEXT NOT NULL REFERENCES "AuthorizationLine"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("authorization_line_id" IS NULL OR length(trim("authorization_line_id"))>0),
"shipped_quantity" INTEGER NOT NULL CHECK("shipped_quantity" >= 1),
"received_quantity" INTEGER NOT NULL CHECK("received_quantity" >= 0),
UNIQUE(shipment_id,authorization_line_id),
CHECK(received_quantity<=shipped_quantity)) STRICT;
CREATE INDEX IF NOT EXISTS "ix_ShipmentLine_shipment_id" ON "ShipmentLine"("shipment_id");
CREATE INDEX IF NOT EXISTS "ix_ShipmentLine_authorization_line_id" ON "ShipmentLine"("authorization_line_id");
CREATE TRIGGER IF NOT EXISTS "ShipmentLine_immutable_id" BEFORE UPDATE OF id ON "ShipmentLine"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "Inspection" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'INS-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"shipment_line_id" TEXT NOT NULL REFERENCES "ShipmentLine"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("shipment_line_id" IS NULL OR length(trim("shipment_line_id"))>0),
"inspected_quantity" INTEGER NOT NULL CHECK("inspected_quantity" >= 1),
"condition" TEXT NOT NULL CHECK("condition" IS NULL OR length(trim("condition"))>0) CHECK("condition" IN ('SELLABLE','REPAIRABLE','UNSAFE','IRREPARABLE')),
"inspected_at" TEXT NOT NULL CHECK("inspected_at" IS NULL OR length(trim("inspected_at"))>0) CHECK(length("inspected_at")=20 AND "inspected_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
"state" TEXT NOT NULL CHECK("state" IS NULL OR length(trim("state"))>0) CHECK("state" IN ('RECORDED','FINALIZED'))) STRICT;
CREATE INDEX IF NOT EXISTS "ix_Inspection_shipment_line_id" ON "Inspection"("shipment_line_id");
CREATE TRIGGER IF NOT EXISTS "Inspection_immutable_id" BEFORE UPDATE OF id ON "Inspection"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "RefundObligation" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'RFO-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"return_line_id" TEXT NOT NULL REFERENCES "ReturnLine"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("return_line_id" IS NULL OR length(trim("return_line_id"))>0),
"inspection_id" TEXT REFERENCES "Inspection"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("inspection_id" IS NULL OR length(trim("inspection_id"))>0),
"entitlement_minor" INTEGER NOT NULL CHECK("entitlement_minor" >= 0),
"fee_minor" INTEGER NOT NULL CHECK("fee_minor" >= 0),
UNIQUE(inspection_id)) STRICT;
CREATE INDEX IF NOT EXISTS "ix_RefundObligation_return_line_id" ON "RefundObligation"("return_line_id");
CREATE INDEX IF NOT EXISTS "ix_RefundObligation_inspection_id" ON "RefundObligation"("inspection_id");
CREATE TRIGGER IF NOT EXISTS "RefundObligation_immutable_id" BEFORE UPDATE OF id ON "RefundObligation"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "Refund" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'REF-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"obligation_id" TEXT NOT NULL REFERENCES "RefundObligation"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("obligation_id" IS NULL OR length(trim("obligation_id"))>0),
"payment_key" TEXT NOT NULL CHECK("payment_key" IS NULL OR length(trim("payment_key"))>0),
"requested_minor" INTEGER NOT NULL CHECK("requested_minor" >= 0),
"paid_minor" INTEGER NOT NULL CHECK("paid_minor" >= 0),
"attempted_at" TEXT NOT NULL CHECK("attempted_at" IS NULL OR length(trim("attempted_at"))>0) CHECK(length("attempted_at")=20 AND "attempted_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
"reason_code" TEXT CHECK("reason_code" IS NULL OR length(trim("reason_code"))>0),
"state" TEXT NOT NULL CHECK("state" IS NULL OR length(trim("state"))>0) CHECK("state" IN ('REQUESTED','REJECTED','FAILED','SUCCEEDED')),
CHECK((state='SUCCEEDED' AND paid_minor=requested_minor AND paid_minor>0) OR (state<>'SUCCEEDED' AND paid_minor=0)),
CHECK(state='REQUESTED' OR reason_code IS NOT NULL)) STRICT;
CREATE INDEX IF NOT EXISTS "ix_Refund_obligation_id" ON "Refund"("obligation_id");
CREATE TRIGGER IF NOT EXISTS "Refund_immutable_id" BEFORE UPDATE OF id ON "Refund"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "InventoryDisposition" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'DSP-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"return_line_id" TEXT NOT NULL REFERENCES "ReturnLine"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("return_line_id" IS NULL OR length(trim("return_line_id"))>0),
"inspection_id" TEXT REFERENCES "Inspection"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("inspection_id" IS NULL OR length(trim("inspection_id"))>0),
"action" TEXT NOT NULL CHECK("action" IS NULL OR length(trim("action"))>0) CHECK("action" IN ('RESTOCK','REFURBISH','QUARANTINE','SCRAP')),
"quantity" INTEGER NOT NULL CHECK("quantity" >= 1),
"decided_at" TEXT NOT NULL CHECK("decided_at" IS NULL OR length(trim("decided_at"))>0) CHECK(length("decided_at")=20 AND "decided_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
"reason_code" TEXT CHECK("reason_code" IS NULL OR length(trim("reason_code"))>0),
"state" TEXT NOT NULL CHECK("state" IS NULL OR length(trim("state"))>0) CHECK("state" IN ('PROPOSED','REJECTED','ACCEPTED')),
CHECK(state<>'ACCEPTED' OR inspection_id IS NOT NULL)) STRICT;
CREATE INDEX IF NOT EXISTS "ix_InventoryDisposition_return_line_id" ON "InventoryDisposition"("return_line_id");
CREATE INDEX IF NOT EXISTS "ix_InventoryDisposition_inspection_id" ON "InventoryDisposition"("inspection_id");
CREATE TRIGGER IF NOT EXISTS "InventoryDisposition_immutable_id" BEFORE UPDATE OF id ON "InventoryDisposition"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "InventoryMovement" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'MOV-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"disposition_id" TEXT NOT NULL REFERENCES "InventoryDisposition"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("disposition_id" IS NULL OR length(trim("disposition_id"))>0),
"quantity" INTEGER NOT NULL CHECK("quantity" >= 1),
"moved_at" TEXT NOT NULL CHECK("moved_at" IS NULL OR length(trim("moved_at"))>0) CHECK(length("moved_at")=20 AND "moved_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
UNIQUE(disposition_id)) STRICT;
CREATE INDEX IF NOT EXISTS "ix_InventoryMovement_disposition_id" ON "InventoryMovement"("disposition_id");
CREATE TRIGGER IF NOT EXISTS "InventoryMovement_immutable_id" BEFORE UPDATE OF id ON "InventoryMovement"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "ActionAttempt" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'ATT-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"Customer_id" TEXT REFERENCES "Customer"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("Customer_id" IS NULL OR length(trim("Customer_id"))>0),
"Product_id" TEXT REFERENCES "Product"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("Product_id" IS NULL OR length(trim("Product_id"))>0),
"ReturnPolicy_id" TEXT REFERENCES "ReturnPolicy"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("ReturnPolicy_id" IS NULL OR length(trim("ReturnPolicy_id"))>0),
"Order_id" TEXT REFERENCES "Order"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("Order_id" IS NULL OR length(trim("Order_id"))>0),
"OrderLine_id" TEXT REFERENCES "OrderLine"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("OrderLine_id" IS NULL OR length(trim("OrderLine_id"))>0),
"ReturnRequest_id" TEXT REFERENCES "ReturnRequest"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("ReturnRequest_id" IS NULL OR length(trim("ReturnRequest_id"))>0),
"ReturnLine_id" TEXT REFERENCES "ReturnLine"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("ReturnLine_id" IS NULL OR length(trim("ReturnLine_id"))>0),
"ReturnAuthorization_id" TEXT REFERENCES "ReturnAuthorization"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("ReturnAuthorization_id" IS NULL OR length(trim("ReturnAuthorization_id"))>0),
"AuthorizationLine_id" TEXT REFERENCES "AuthorizationLine"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("AuthorizationLine_id" IS NULL OR length(trim("AuthorizationLine_id"))>0),
"ReturnShipment_id" TEXT REFERENCES "ReturnShipment"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("ReturnShipment_id" IS NULL OR length(trim("ReturnShipment_id"))>0),
"ShipmentLine_id" TEXT REFERENCES "ShipmentLine"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("ShipmentLine_id" IS NULL OR length(trim("ShipmentLine_id"))>0),
"Inspection_id" TEXT REFERENCES "Inspection"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("Inspection_id" IS NULL OR length(trim("Inspection_id"))>0),
"RefundObligation_id" TEXT REFERENCES "RefundObligation"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("RefundObligation_id" IS NULL OR length(trim("RefundObligation_id"))>0),
"Refund_id" TEXT REFERENCES "Refund"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("Refund_id" IS NULL OR length(trim("Refund_id"))>0),
"InventoryDisposition_id" TEXT REFERENCES "InventoryDisposition"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("InventoryDisposition_id" IS NULL OR length(trim("InventoryDisposition_id"))>0),
"InventoryMovement_id" TEXT REFERENCES "InventoryMovement"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("InventoryMovement_id" IS NULL OR length(trim("InventoryMovement_id"))>0),
"action" TEXT NOT NULL CHECK("action" IS NULL OR length(trim("action"))>0),
"payload_json" TEXT NOT NULL CHECK("payload_json" IS NULL OR length(trim("payload_json"))>0) CHECK(json_valid(payload_json)),
"decision" TEXT NOT NULL CHECK("decision" IS NULL OR length(trim("decision"))>0) CHECK("decision" IN ('PENDING','ALLOWED','BLOCKED','FAILED')),
"reason_code" TEXT CHECK("reason_code" IS NULL OR length(trim("reason_code"))>0),
"attempted_at" TEXT NOT NULL CHECK("attempted_at" IS NULL OR length(trim("attempted_at"))>0) CHECK(length("attempted_at")=20 AND "attempted_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
"correlation_id" TEXT NOT NULL CHECK("correlation_id" IS NULL OR length(trim("correlation_id"))>0),
CHECK(("Customer_id" IS NOT NULL)+("Product_id" IS NOT NULL)+("ReturnPolicy_id" IS NOT NULL)+("Order_id" IS NOT NULL)+("OrderLine_id" IS NOT NULL)+("ReturnRequest_id" IS NOT NULL)+("ReturnLine_id" IS NOT NULL)+("ReturnAuthorization_id" IS NOT NULL)+("AuthorizationLine_id" IS NOT NULL)+("ReturnShipment_id" IS NOT NULL)+("ShipmentLine_id" IS NOT NULL)+("Inspection_id" IS NOT NULL)+("RefundObligation_id" IS NOT NULL)+("Refund_id" IS NOT NULL)+("InventoryDisposition_id" IS NOT NULL)+("InventoryMovement_id" IS NOT NULL)=1)) STRICT;
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_Customer_id" ON "ActionAttempt"("Customer_id");
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_Product_id" ON "ActionAttempt"("Product_id");
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_ReturnPolicy_id" ON "ActionAttempt"("ReturnPolicy_id");
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_Order_id" ON "ActionAttempt"("Order_id");
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_OrderLine_id" ON "ActionAttempt"("OrderLine_id");
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_ReturnRequest_id" ON "ActionAttempt"("ReturnRequest_id");
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_ReturnLine_id" ON "ActionAttempt"("ReturnLine_id");
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_ReturnAuthorization_id" ON "ActionAttempt"("ReturnAuthorization_id");
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_AuthorizationLine_id" ON "ActionAttempt"("AuthorizationLine_id");
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_ReturnShipment_id" ON "ActionAttempt"("ReturnShipment_id");
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_ShipmentLine_id" ON "ActionAttempt"("ShipmentLine_id");
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_Inspection_id" ON "ActionAttempt"("Inspection_id");
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_RefundObligation_id" ON "ActionAttempt"("RefundObligation_id");
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_Refund_id" ON "ActionAttempt"("Refund_id");
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_InventoryDisposition_id" ON "ActionAttempt"("InventoryDisposition_id");
CREATE INDEX IF NOT EXISTS "ix_ActionAttempt_InventoryMovement_id" ON "ActionAttempt"("InventoryMovement_id");
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_id" BEFORE UPDATE OF id ON "ActionAttempt"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE TABLE IF NOT EXISTS "EventLog" ("id" TEXT NOT NULL PRIMARY KEY CHECK("id" IS NULL OR length(trim("id"))>0) CHECK(id GLOB 'EVT-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'),
"Customer_id" TEXT REFERENCES "Customer"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("Customer_id" IS NULL OR length(trim("Customer_id"))>0),
"Product_id" TEXT REFERENCES "Product"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("Product_id" IS NULL OR length(trim("Product_id"))>0),
"ReturnPolicy_id" TEXT REFERENCES "ReturnPolicy"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("ReturnPolicy_id" IS NULL OR length(trim("ReturnPolicy_id"))>0),
"Order_id" TEXT REFERENCES "Order"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("Order_id" IS NULL OR length(trim("Order_id"))>0),
"OrderLine_id" TEXT REFERENCES "OrderLine"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("OrderLine_id" IS NULL OR length(trim("OrderLine_id"))>0),
"ReturnRequest_id" TEXT REFERENCES "ReturnRequest"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("ReturnRequest_id" IS NULL OR length(trim("ReturnRequest_id"))>0),
"ReturnLine_id" TEXT REFERENCES "ReturnLine"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("ReturnLine_id" IS NULL OR length(trim("ReturnLine_id"))>0),
"ReturnAuthorization_id" TEXT REFERENCES "ReturnAuthorization"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("ReturnAuthorization_id" IS NULL OR length(trim("ReturnAuthorization_id"))>0),
"AuthorizationLine_id" TEXT REFERENCES "AuthorizationLine"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("AuthorizationLine_id" IS NULL OR length(trim("AuthorizationLine_id"))>0),
"ReturnShipment_id" TEXT REFERENCES "ReturnShipment"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("ReturnShipment_id" IS NULL OR length(trim("ReturnShipment_id"))>0),
"ShipmentLine_id" TEXT REFERENCES "ShipmentLine"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("ShipmentLine_id" IS NULL OR length(trim("ShipmentLine_id"))>0),
"Inspection_id" TEXT REFERENCES "Inspection"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("Inspection_id" IS NULL OR length(trim("Inspection_id"))>0),
"RefundObligation_id" TEXT REFERENCES "RefundObligation"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("RefundObligation_id" IS NULL OR length(trim("RefundObligation_id"))>0),
"Refund_id" TEXT REFERENCES "Refund"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("Refund_id" IS NULL OR length(trim("Refund_id"))>0),
"InventoryDisposition_id" TEXT REFERENCES "InventoryDisposition"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("InventoryDisposition_id" IS NULL OR length(trim("InventoryDisposition_id"))>0),
"InventoryMovement_id" TEXT REFERENCES "InventoryMovement"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("InventoryMovement_id" IS NULL OR length(trim("InventoryMovement_id"))>0),
"attempt_id" TEXT REFERENCES "ActionAttempt"(id) ON UPDATE RESTRICT ON DELETE RESTRICT CHECK("attempt_id" IS NULL OR length(trim("attempt_id"))>0),
"event_type" TEXT NOT NULL CHECK("event_type" IS NULL OR length(trim("event_type"))>0) CHECK("event_type" IN ('CREATED','STATE_CHANGED','OBSERVED')),
"previous_state" TEXT CHECK("previous_state" IS NULL OR length(trim("previous_state"))>0),
"new_state" TEXT CHECK("new_state" IS NULL OR length(trim("new_state"))>0),
"occurred_at" TEXT NOT NULL CHECK("occurred_at" IS NULL OR length(trim("occurred_at"))>0) CHECK(length("occurred_at")=20 AND "occurred_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'),
"reason_code" TEXT NOT NULL CHECK("reason_code" IS NULL OR length(trim("reason_code"))>0),
"correlation_id" TEXT NOT NULL CHECK("correlation_id" IS NULL OR length(trim("correlation_id"))>0),
CHECK(("Customer_id" IS NOT NULL)+("Product_id" IS NOT NULL)+("ReturnPolicy_id" IS NOT NULL)+("Order_id" IS NOT NULL)+("OrderLine_id" IS NOT NULL)+("ReturnRequest_id" IS NOT NULL)+("ReturnLine_id" IS NOT NULL)+("ReturnAuthorization_id" IS NOT NULL)+("AuthorizationLine_id" IS NOT NULL)+("ReturnShipment_id" IS NOT NULL)+("ShipmentLine_id" IS NOT NULL)+("Inspection_id" IS NOT NULL)+("RefundObligation_id" IS NOT NULL)+("Refund_id" IS NOT NULL)+("InventoryDisposition_id" IS NOT NULL)+("InventoryMovement_id" IS NOT NULL)=1)) STRICT;
CREATE INDEX IF NOT EXISTS "ix_EventLog_Customer_id" ON "EventLog"("Customer_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_Product_id" ON "EventLog"("Product_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_ReturnPolicy_id" ON "EventLog"("ReturnPolicy_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_Order_id" ON "EventLog"("Order_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_OrderLine_id" ON "EventLog"("OrderLine_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_ReturnRequest_id" ON "EventLog"("ReturnRequest_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_ReturnLine_id" ON "EventLog"("ReturnLine_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_ReturnAuthorization_id" ON "EventLog"("ReturnAuthorization_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_AuthorizationLine_id" ON "EventLog"("AuthorizationLine_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_ReturnShipment_id" ON "EventLog"("ReturnShipment_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_ShipmentLine_id" ON "EventLog"("ShipmentLine_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_Inspection_id" ON "EventLog"("Inspection_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_RefundObligation_id" ON "EventLog"("RefundObligation_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_Refund_id" ON "EventLog"("Refund_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_InventoryDisposition_id" ON "EventLog"("InventoryDisposition_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_InventoryMovement_id" ON "EventLog"("InventoryMovement_id");
CREATE INDEX IF NOT EXISTS "ix_EventLog_attempt_id" ON "EventLog"("attempt_id");
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_id" BEFORE UPDATE OF id ON "EventLog"
            WHEN NEW.id<>OLD.id BEGIN SELECT RAISE(ABORT,'immutable identifier'); END;
CREATE UNIQUE INDEX IF NOT EXISTS one_success_per_payment_key ON Refund(payment_key) WHERE state='SUCCEEDED';
CREATE INDEX IF NOT EXISTS event_time ON EventLog(occurred_at,id);
CREATE VIEW IF NOT EXISTS EventHistory AS SELECT *, CASE WHEN "Customer_id" IS NOT NULL THEN 'Customer' WHEN "Product_id" IS NOT NULL THEN 'Product' WHEN "ReturnPolicy_id" IS NOT NULL THEN 'ReturnPolicy' WHEN "Order_id" IS NOT NULL THEN 'Order' WHEN "OrderLine_id" IS NOT NULL THEN 'OrderLine' WHEN "ReturnRequest_id" IS NOT NULL THEN 'ReturnRequest' WHEN "ReturnLine_id" IS NOT NULL THEN 'ReturnLine' WHEN "ReturnAuthorization_id" IS NOT NULL THEN 'ReturnAuthorization' WHEN "AuthorizationLine_id" IS NOT NULL THEN 'AuthorizationLine' WHEN "ReturnShipment_id" IS NOT NULL THEN 'ReturnShipment' WHEN "ShipmentLine_id" IS NOT NULL THEN 'ShipmentLine' WHEN "Inspection_id" IS NOT NULL THEN 'Inspection' WHEN "RefundObligation_id" IS NOT NULL THEN 'RefundObligation' WHEN "Refund_id" IS NOT NULL THEN 'Refund' WHEN "InventoryDisposition_id" IS NOT NULL THEN 'InventoryDisposition' WHEN "InventoryMovement_id" IS NOT NULL THEN 'InventoryMovement' END AS entity_type, COALESCE("Customer_id","Product_id","ReturnPolicy_id","Order_id","OrderLine_id","ReturnRequest_id","ReturnLine_id","ReturnAuthorization_id","AuthorizationLine_id","ReturnShipment_id","ShipmentLine_id","Inspection_id","RefundObligation_id","Refund_id","InventoryDisposition_id","InventoryMovement_id") AS entity_id FROM EventLog;
CREATE TRIGGER IF NOT EXISTS EventLog_append_only_UPDATE BEFORE UPDATE ON "EventLog"
                BEGIN SELECT RAISE(ABORT,'append-only record'); END;
CREATE TRIGGER IF NOT EXISTS EventLog_append_only_DELETE BEFORE DELETE ON "EventLog"
                BEGIN SELECT RAISE(ABORT,'append-only record'); END;
CREATE TRIGGER IF NOT EXISTS InventoryMovement_append_only_UPDATE BEFORE UPDATE ON "InventoryMovement"
                BEGIN SELECT RAISE(ABORT,'append-only record'); END;
CREATE TRIGGER IF NOT EXISTS InventoryMovement_append_only_DELETE BEFORE DELETE ON "InventoryMovement"
                BEGIN SELECT RAISE(ABORT,'append-only record'); END;
CREATE TRIGGER IF NOT EXISTS ActionAttempt_append_only_UPDATE BEFORE UPDATE ON "ActionAttempt"
                BEGIN SELECT RAISE(ABORT,'append-only record'); END;
CREATE TRIGGER IF NOT EXISTS ActionAttempt_append_only_DELETE BEFORE DELETE ON "ActionAttempt"
                BEGIN SELECT RAISE(ABORT,'append-only record'); END;
CREATE TRIGGER IF NOT EXISTS "Order_immutable_customer_id" BEFORE UPDATE OF "customer_id" ON "Order"
                    WHEN NEW."customer_id" IS NOT OLD."customer_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "OrderLine_immutable_order_id" BEFORE UPDATE OF "order_id" ON "OrderLine"
                    WHEN NEW."order_id" IS NOT OLD."order_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "OrderLine_immutable_product_id" BEFORE UPDATE OF "product_id" ON "OrderLine"
                    WHEN NEW."product_id" IS NOT OLD."product_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ReturnRequest_immutable_order_id" BEFORE UPDATE OF "order_id" ON "ReturnRequest"
                    WHEN NEW."order_id" IS NOT OLD."order_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ReturnRequest_immutable_policy_id" BEFORE UPDATE OF "policy_id" ON "ReturnRequest"
                    WHEN NEW."policy_id" IS NOT OLD."policy_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ReturnLine_immutable_request_id" BEFORE UPDATE OF "request_id" ON "ReturnLine"
                    WHEN NEW."request_id" IS NOT OLD."request_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ReturnLine_immutable_order_line_id" BEFORE UPDATE OF "order_line_id" ON "ReturnLine"
                    WHEN NEW."order_line_id" IS NOT OLD."order_line_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ReturnAuthorization_immutable_request_id" BEFORE UPDATE OF "request_id" ON "ReturnAuthorization"
                    WHEN NEW."request_id" IS NOT OLD."request_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "AuthorizationLine_immutable_authorization_id" BEFORE UPDATE OF "authorization_id" ON "AuthorizationLine"
                    WHEN NEW."authorization_id" IS NOT OLD."authorization_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "AuthorizationLine_immutable_return_line_id" BEFORE UPDATE OF "return_line_id" ON "AuthorizationLine"
                    WHEN NEW."return_line_id" IS NOT OLD."return_line_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ShipmentLine_immutable_shipment_id" BEFORE UPDATE OF "shipment_id" ON "ShipmentLine"
                    WHEN NEW."shipment_id" IS NOT OLD."shipment_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ShipmentLine_immutable_authorization_line_id" BEFORE UPDATE OF "authorization_line_id" ON "ShipmentLine"
                    WHEN NEW."authorization_line_id" IS NOT OLD."authorization_line_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "Inspection_immutable_shipment_line_id" BEFORE UPDATE OF "shipment_line_id" ON "Inspection"
                    WHEN NEW."shipment_line_id" IS NOT OLD."shipment_line_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "RefundObligation_immutable_return_line_id" BEFORE UPDATE OF "return_line_id" ON "RefundObligation"
                    WHEN NEW."return_line_id" IS NOT OLD."return_line_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "RefundObligation_immutable_inspection_id" BEFORE UPDATE OF "inspection_id" ON "RefundObligation"
                    WHEN NEW."inspection_id" IS NOT OLD."inspection_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "Refund_immutable_obligation_id" BEFORE UPDATE OF "obligation_id" ON "Refund"
                    WHEN NEW."obligation_id" IS NOT OLD."obligation_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "InventoryDisposition_immutable_return_line_id" BEFORE UPDATE OF "return_line_id" ON "InventoryDisposition"
                    WHEN NEW."return_line_id" IS NOT OLD."return_line_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "InventoryDisposition_immutable_inspection_id" BEFORE UPDATE OF "inspection_id" ON "InventoryDisposition"
                    WHEN NEW."inspection_id" IS NOT OLD."inspection_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "InventoryMovement_immutable_disposition_id" BEFORE UPDATE OF "disposition_id" ON "InventoryMovement"
                    WHEN NEW."disposition_id" IS NOT OLD."disposition_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_Customer_id" BEFORE UPDATE OF "Customer_id" ON "ActionAttempt"
                    WHEN NEW."Customer_id" IS NOT OLD."Customer_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_Product_id" BEFORE UPDATE OF "Product_id" ON "ActionAttempt"
                    WHEN NEW."Product_id" IS NOT OLD."Product_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_ReturnPolicy_id" BEFORE UPDATE OF "ReturnPolicy_id" ON "ActionAttempt"
                    WHEN NEW."ReturnPolicy_id" IS NOT OLD."ReturnPolicy_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_Order_id" BEFORE UPDATE OF "Order_id" ON "ActionAttempt"
                    WHEN NEW."Order_id" IS NOT OLD."Order_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_OrderLine_id" BEFORE UPDATE OF "OrderLine_id" ON "ActionAttempt"
                    WHEN NEW."OrderLine_id" IS NOT OLD."OrderLine_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_ReturnRequest_id" BEFORE UPDATE OF "ReturnRequest_id" ON "ActionAttempt"
                    WHEN NEW."ReturnRequest_id" IS NOT OLD."ReturnRequest_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_ReturnLine_id" BEFORE UPDATE OF "ReturnLine_id" ON "ActionAttempt"
                    WHEN NEW."ReturnLine_id" IS NOT OLD."ReturnLine_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_ReturnAuthorization_id" BEFORE UPDATE OF "ReturnAuthorization_id" ON "ActionAttempt"
                    WHEN NEW."ReturnAuthorization_id" IS NOT OLD."ReturnAuthorization_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_AuthorizationLine_id" BEFORE UPDATE OF "AuthorizationLine_id" ON "ActionAttempt"
                    WHEN NEW."AuthorizationLine_id" IS NOT OLD."AuthorizationLine_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_ReturnShipment_id" BEFORE UPDATE OF "ReturnShipment_id" ON "ActionAttempt"
                    WHEN NEW."ReturnShipment_id" IS NOT OLD."ReturnShipment_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_ShipmentLine_id" BEFORE UPDATE OF "ShipmentLine_id" ON "ActionAttempt"
                    WHEN NEW."ShipmentLine_id" IS NOT OLD."ShipmentLine_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_Inspection_id" BEFORE UPDATE OF "Inspection_id" ON "ActionAttempt"
                    WHEN NEW."Inspection_id" IS NOT OLD."Inspection_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_RefundObligation_id" BEFORE UPDATE OF "RefundObligation_id" ON "ActionAttempt"
                    WHEN NEW."RefundObligation_id" IS NOT OLD."RefundObligation_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_Refund_id" BEFORE UPDATE OF "Refund_id" ON "ActionAttempt"
                    WHEN NEW."Refund_id" IS NOT OLD."Refund_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_InventoryDisposition_id" BEFORE UPDATE OF "InventoryDisposition_id" ON "ActionAttempt"
                    WHEN NEW."InventoryDisposition_id" IS NOT OLD."InventoryDisposition_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "ActionAttempt_immutable_InventoryMovement_id" BEFORE UPDATE OF "InventoryMovement_id" ON "ActionAttempt"
                    WHEN NEW."InventoryMovement_id" IS NOT OLD."InventoryMovement_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_Customer_id" BEFORE UPDATE OF "Customer_id" ON "EventLog"
                    WHEN NEW."Customer_id" IS NOT OLD."Customer_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_Product_id" BEFORE UPDATE OF "Product_id" ON "EventLog"
                    WHEN NEW."Product_id" IS NOT OLD."Product_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_ReturnPolicy_id" BEFORE UPDATE OF "ReturnPolicy_id" ON "EventLog"
                    WHEN NEW."ReturnPolicy_id" IS NOT OLD."ReturnPolicy_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_Order_id" BEFORE UPDATE OF "Order_id" ON "EventLog"
                    WHEN NEW."Order_id" IS NOT OLD."Order_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_OrderLine_id" BEFORE UPDATE OF "OrderLine_id" ON "EventLog"
                    WHEN NEW."OrderLine_id" IS NOT OLD."OrderLine_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_ReturnRequest_id" BEFORE UPDATE OF "ReturnRequest_id" ON "EventLog"
                    WHEN NEW."ReturnRequest_id" IS NOT OLD."ReturnRequest_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_ReturnLine_id" BEFORE UPDATE OF "ReturnLine_id" ON "EventLog"
                    WHEN NEW."ReturnLine_id" IS NOT OLD."ReturnLine_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_ReturnAuthorization_id" BEFORE UPDATE OF "ReturnAuthorization_id" ON "EventLog"
                    WHEN NEW."ReturnAuthorization_id" IS NOT OLD."ReturnAuthorization_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_AuthorizationLine_id" BEFORE UPDATE OF "AuthorizationLine_id" ON "EventLog"
                    WHEN NEW."AuthorizationLine_id" IS NOT OLD."AuthorizationLine_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_ReturnShipment_id" BEFORE UPDATE OF "ReturnShipment_id" ON "EventLog"
                    WHEN NEW."ReturnShipment_id" IS NOT OLD."ReturnShipment_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_ShipmentLine_id" BEFORE UPDATE OF "ShipmentLine_id" ON "EventLog"
                    WHEN NEW."ShipmentLine_id" IS NOT OLD."ShipmentLine_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_Inspection_id" BEFORE UPDATE OF "Inspection_id" ON "EventLog"
                    WHEN NEW."Inspection_id" IS NOT OLD."Inspection_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_RefundObligation_id" BEFORE UPDATE OF "RefundObligation_id" ON "EventLog"
                    WHEN NEW."RefundObligation_id" IS NOT OLD."RefundObligation_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_Refund_id" BEFORE UPDATE OF "Refund_id" ON "EventLog"
                    WHEN NEW."Refund_id" IS NOT OLD."Refund_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_InventoryDisposition_id" BEFORE UPDATE OF "InventoryDisposition_id" ON "EventLog"
                    WHEN NEW."InventoryDisposition_id" IS NOT OLD."InventoryDisposition_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_InventoryMovement_id" BEFORE UPDATE OF "InventoryMovement_id" ON "EventLog"
                    WHEN NEW."InventoryMovement_id" IS NOT OLD."InventoryMovement_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS "EventLog_immutable_attempt_id" BEFORE UPDATE OF "attempt_id" ON "EventLog"
                    WHEN NEW."attempt_id" IS NOT OLD."attempt_id" BEGIN SELECT RAISE(ABORT,'immutable relationship'); END;
CREATE TRIGGER IF NOT EXISTS Customer_state_history BEFORE UPDATE OF state ON "Customer"
            WHEN NEW.state<>OLD.state AND NOT EXISTS (
                SELECT 1 FROM EventLog e WHERE e.id=(SELECT id FROM EventLog WHERE "Customer_id"=OLD.id ORDER BY rowid DESC LIMIT 1)
                AND e.previous_state=OLD.state AND e.new_state=NEW.state AND e.event_type='STATE_CHANGED')
            BEGIN SELECT RAISE(ABORT,'state change requires matching event'); END;
CREATE TRIGGER IF NOT EXISTS event_Customer_transition BEFORE INSERT ON EventLog
            WHEN NEW."Customer_id" IS NOT NULL AND NEW.event_type='STATE_CHANGED'
            BEGIN
                SELECT CASE WHEN NOT ((NEW.previous_state='ACTIVE' AND NEW.new_state IN ('INACTIVE')) OR (NEW.previous_state='INACTIVE' AND NEW.new_state IN ('ACTIVE'))) OR NEW.previous_state IS NULL OR NEW.new_state IS NULL
                    OR NEW.previous_state IS NOT (SELECT state FROM "Customer" WHERE id=NEW."Customer_id")
                    THEN RAISE(ABORT,'invalid state transition') END;
            END;
CREATE TRIGGER IF NOT EXISTS Order_state_history BEFORE UPDATE OF state ON "Order"
            WHEN NEW.state<>OLD.state AND NOT EXISTS (
                SELECT 1 FROM EventLog e WHERE e.id=(SELECT id FROM EventLog WHERE "Order_id"=OLD.id ORDER BY rowid DESC LIMIT 1)
                AND e.previous_state=OLD.state AND e.new_state=NEW.state AND e.event_type='STATE_CHANGED')
            BEGIN SELECT RAISE(ABORT,'state change requires matching event'); END;
CREATE TRIGGER IF NOT EXISTS event_Order_transition BEFORE INSERT ON EventLog
            WHEN NEW."Order_id" IS NOT NULL AND NEW.event_type='STATE_CHANGED'
            BEGIN
                SELECT CASE WHEN NOT ((NEW.previous_state='PLACED' AND NEW.new_state IN ('FULFILLED')) OR (NEW.previous_state='FULFILLED' AND NEW.new_state IN ('DELIVERED'))) OR NEW.previous_state IS NULL OR NEW.new_state IS NULL
                    OR NEW.previous_state IS NOT (SELECT state FROM "Order" WHERE id=NEW."Order_id")
                    THEN RAISE(ABORT,'invalid state transition') END;
            END;
CREATE TRIGGER IF NOT EXISTS ReturnRequest_state_history BEFORE UPDATE OF state ON "ReturnRequest"
            WHEN NEW.state<>OLD.state AND NOT EXISTS (
                SELECT 1 FROM EventLog e WHERE e.id=(SELECT id FROM EventLog WHERE "ReturnRequest_id"=OLD.id ORDER BY rowid DESC LIMIT 1)
                AND e.previous_state=OLD.state AND e.new_state=NEW.state AND e.event_type='STATE_CHANGED')
            BEGIN SELECT RAISE(ABORT,'state change requires matching event'); END;
CREATE TRIGGER IF NOT EXISTS event_ReturnRequest_transition BEFORE INSERT ON EventLog
            WHEN NEW."ReturnRequest_id" IS NOT NULL AND NEW.event_type='STATE_CHANGED'
            BEGIN
                SELECT CASE WHEN NOT ((NEW.previous_state='REQUESTED' AND NEW.new_state IN ('APPROVED','PARTIALLY_APPROVED','REJECTED','CANCELLED')) OR (NEW.previous_state='APPROVED' AND NEW.new_state IN ('IN_TRANSIT','CANCELLED')) OR (NEW.previous_state='PARTIALLY_APPROVED' AND NEW.new_state IN ('IN_TRANSIT','CANCELLED')) OR (NEW.previous_state='IN_TRANSIT' AND NEW.new_state IN ('RECEIVED')) OR (NEW.previous_state='RECEIVED' AND NEW.new_state IN ('INSPECTED')) OR (NEW.previous_state='INSPECTED' AND NEW.new_state IN ('CLOSED'))) OR NEW.previous_state IS NULL OR NEW.new_state IS NULL
                    OR NEW.previous_state IS NOT (SELECT state FROM "ReturnRequest" WHERE id=NEW."ReturnRequest_id")
                    THEN RAISE(ABORT,'invalid state transition') END;
            END;
CREATE TRIGGER IF NOT EXISTS ReturnLine_state_history BEFORE UPDATE OF state ON "ReturnLine"
            WHEN NEW.state<>OLD.state AND NOT EXISTS (
                SELECT 1 FROM EventLog e WHERE e.id=(SELECT id FROM EventLog WHERE "ReturnLine_id"=OLD.id ORDER BY rowid DESC LIMIT 1)
                AND e.previous_state=OLD.state AND e.new_state=NEW.state AND e.event_type='STATE_CHANGED')
            BEGIN SELECT RAISE(ABORT,'state change requires matching event'); END;
CREATE TRIGGER IF NOT EXISTS event_ReturnLine_transition BEFORE INSERT ON EventLog
            WHEN NEW."ReturnLine_id" IS NOT NULL AND NEW.event_type='STATE_CHANGED'
            BEGIN
                SELECT CASE WHEN NOT ((NEW.previous_state='REQUESTED' AND NEW.new_state IN ('APPROVED','PARTIALLY_APPROVED','REJECTED','CANCELLED')) OR (NEW.previous_state='APPROVED' AND NEW.new_state IN ('SHIPPED','CANCELLED')) OR (NEW.previous_state='PARTIALLY_APPROVED' AND NEW.new_state IN ('SHIPPED','CANCELLED')) OR (NEW.previous_state='SHIPPED' AND NEW.new_state IN ('RECEIVED')) OR (NEW.previous_state='RECEIVED' AND NEW.new_state IN ('INSPECTED')) OR (NEW.previous_state='INSPECTED' AND NEW.new_state IN ('SETTLED'))) OR NEW.previous_state IS NULL OR NEW.new_state IS NULL
                    OR NEW.previous_state IS NOT (SELECT state FROM "ReturnLine" WHERE id=NEW."ReturnLine_id")
                    THEN RAISE(ABORT,'invalid state transition') END;
            END;
CREATE TRIGGER IF NOT EXISTS ReturnAuthorization_state_history BEFORE UPDATE OF state ON "ReturnAuthorization"
            WHEN NEW.state<>OLD.state AND NOT EXISTS (
                SELECT 1 FROM EventLog e WHERE e.id=(SELECT id FROM EventLog WHERE "ReturnAuthorization_id"=OLD.id ORDER BY rowid DESC LIMIT 1)
                AND e.previous_state=OLD.state AND e.new_state=NEW.state AND e.event_type='STATE_CHANGED')
            BEGIN SELECT RAISE(ABORT,'state change requires matching event'); END;
CREATE TRIGGER IF NOT EXISTS event_ReturnAuthorization_transition BEFORE INSERT ON EventLog
            WHEN NEW."ReturnAuthorization_id" IS NOT NULL AND NEW.event_type='STATE_CHANGED'
            BEGIN
                SELECT CASE WHEN NOT ((NEW.previous_state='ISSUED' AND NEW.new_state IN ('SUPERSEDED','CANCELLED','CONSUMED'))) OR NEW.previous_state IS NULL OR NEW.new_state IS NULL
                    OR NEW.previous_state IS NOT (SELECT state FROM "ReturnAuthorization" WHERE id=NEW."ReturnAuthorization_id")
                    THEN RAISE(ABORT,'invalid state transition') END;
            END;
CREATE TRIGGER IF NOT EXISTS ReturnShipment_state_history BEFORE UPDATE OF state ON "ReturnShipment"
            WHEN NEW.state<>OLD.state AND NOT EXISTS (
                SELECT 1 FROM EventLog e WHERE e.id=(SELECT id FROM EventLog WHERE "ReturnShipment_id"=OLD.id ORDER BY rowid DESC LIMIT 1)
                AND e.previous_state=OLD.state AND e.new_state=NEW.state AND e.event_type='STATE_CHANGED')
            BEGIN SELECT RAISE(ABORT,'state change requires matching event'); END;
CREATE TRIGGER IF NOT EXISTS event_ReturnShipment_transition BEFORE INSERT ON EventLog
            WHEN NEW."ReturnShipment_id" IS NOT NULL AND NEW.event_type='STATE_CHANGED'
            BEGIN
                SELECT CASE WHEN NOT ((NEW.previous_state='CREATED' AND NEW.new_state IN ('DISPATCHED')) OR (NEW.previous_state='DISPATCHED' AND NEW.new_state IN ('DELIVERED','MISSING'))) OR NEW.previous_state IS NULL OR NEW.new_state IS NULL
                    OR NEW.previous_state IS NOT (SELECT state FROM "ReturnShipment" WHERE id=NEW."ReturnShipment_id")
                    THEN RAISE(ABORT,'invalid state transition') END;
            END;
CREATE TRIGGER IF NOT EXISTS Inspection_state_history BEFORE UPDATE OF state ON "Inspection"
            WHEN NEW.state<>OLD.state AND NOT EXISTS (
                SELECT 1 FROM EventLog e WHERE e.id=(SELECT id FROM EventLog WHERE "Inspection_id"=OLD.id ORDER BY rowid DESC LIMIT 1)
                AND e.previous_state=OLD.state AND e.new_state=NEW.state AND e.event_type='STATE_CHANGED')
            BEGIN SELECT RAISE(ABORT,'state change requires matching event'); END;
CREATE TRIGGER IF NOT EXISTS event_Inspection_transition BEFORE INSERT ON EventLog
            WHEN NEW."Inspection_id" IS NOT NULL AND NEW.event_type='STATE_CHANGED'
            BEGIN
                SELECT CASE WHEN NOT ((NEW.previous_state='RECORDED' AND NEW.new_state IN ('FINALIZED'))) OR NEW.previous_state IS NULL OR NEW.new_state IS NULL
                    OR NEW.previous_state IS NOT (SELECT state FROM "Inspection" WHERE id=NEW."Inspection_id")
                    THEN RAISE(ABORT,'invalid state transition') END;
            END;
CREATE TRIGGER IF NOT EXISTS Refund_state_history BEFORE UPDATE OF state ON "Refund"
            WHEN NEW.state<>OLD.state AND NOT EXISTS (
                SELECT 1 FROM EventLog e WHERE e.id=(SELECT id FROM EventLog WHERE "Refund_id"=OLD.id ORDER BY rowid DESC LIMIT 1)
                AND e.previous_state=OLD.state AND e.new_state=NEW.state AND e.event_type='STATE_CHANGED')
            BEGIN SELECT RAISE(ABORT,'state change requires matching event'); END;
CREATE TRIGGER IF NOT EXISTS event_Refund_transition BEFORE INSERT ON EventLog
            WHEN NEW."Refund_id" IS NOT NULL AND NEW.event_type='STATE_CHANGED'
            BEGIN
                SELECT CASE WHEN NOT ((NEW.previous_state='REQUESTED' AND NEW.new_state IN ('REJECTED','FAILED','SUCCEEDED'))) OR NEW.previous_state IS NULL OR NEW.new_state IS NULL
                    OR NEW.previous_state IS NOT (SELECT state FROM "Refund" WHERE id=NEW."Refund_id")
                    THEN RAISE(ABORT,'invalid state transition') END;
            END;
CREATE TRIGGER IF NOT EXISTS InventoryDisposition_state_history BEFORE UPDATE OF state ON "InventoryDisposition"
            WHEN NEW.state<>OLD.state AND NOT EXISTS (
                SELECT 1 FROM EventLog e WHERE e.id=(SELECT id FROM EventLog WHERE "InventoryDisposition_id"=OLD.id ORDER BY rowid DESC LIMIT 1)
                AND e.previous_state=OLD.state AND e.new_state=NEW.state AND e.event_type='STATE_CHANGED')
            BEGIN SELECT RAISE(ABORT,'state change requires matching event'); END;
CREATE TRIGGER IF NOT EXISTS event_InventoryDisposition_transition BEFORE INSERT ON EventLog
            WHEN NEW."InventoryDisposition_id" IS NOT NULL AND NEW.event_type='STATE_CHANGED'
            BEGIN
                SELECT CASE WHEN NOT ((NEW.previous_state='PROPOSED' AND NEW.new_state IN ('REJECTED','ACCEPTED'))) OR NEW.previous_state IS NULL OR NEW.new_state IS NULL
                    OR NEW.previous_state IS NOT (SELECT state FROM "InventoryDisposition" WHERE id=NEW."InventoryDisposition_id")
                    THEN RAISE(ABORT,'invalid state transition') END;
            END;
CREATE TRIGGER IF NOT EXISTS event_Customer_chronology BEFORE INSERT ON EventLog
            WHEN NEW."Customer_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "Customer_id"=NEW."Customer_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE UNIQUE INDEX IF NOT EXISTS event_Customer_one_creation
                ON EventLog("Customer_id") WHERE event_type='CREATED';
CREATE TRIGGER IF NOT EXISTS event_Customer_creation BEFORE INSERT ON EventLog
                WHEN NEW."Customer_id" IS NOT NULL AND NEW.event_type='CREATED'
                AND (NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT (SELECT state FROM "Customer" WHERE id=NEW."Customer_id"))
                BEGIN SELECT RAISE(ABORT,'creation state mismatch'); END;
CREATE TRIGGER IF NOT EXISTS event_Product_chronology BEFORE INSERT ON EventLog
            WHEN NEW."Product_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "Product_id"=NEW."Product_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE TRIGGER IF NOT EXISTS event_Product_stateless BEFORE INSERT ON EventLog
                WHEN NEW."Product_id" IS NOT NULL AND (NEW.event_type='STATE_CHANGED' OR NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT NULL)
                BEGIN SELECT RAISE(ABORT,'stateless entity'); END;
CREATE TRIGGER IF NOT EXISTS event_ReturnPolicy_chronology BEFORE INSERT ON EventLog
            WHEN NEW."ReturnPolicy_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "ReturnPolicy_id"=NEW."ReturnPolicy_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE TRIGGER IF NOT EXISTS event_ReturnPolicy_stateless BEFORE INSERT ON EventLog
                WHEN NEW."ReturnPolicy_id" IS NOT NULL AND (NEW.event_type='STATE_CHANGED' OR NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT NULL)
                BEGIN SELECT RAISE(ABORT,'stateless entity'); END;
CREATE TRIGGER IF NOT EXISTS event_Order_chronology BEFORE INSERT ON EventLog
            WHEN NEW."Order_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "Order_id"=NEW."Order_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE UNIQUE INDEX IF NOT EXISTS event_Order_one_creation
                ON EventLog("Order_id") WHERE event_type='CREATED';
CREATE TRIGGER IF NOT EXISTS event_Order_creation BEFORE INSERT ON EventLog
                WHEN NEW."Order_id" IS NOT NULL AND NEW.event_type='CREATED'
                AND (NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT (SELECT state FROM "Order" WHERE id=NEW."Order_id"))
                BEGIN SELECT RAISE(ABORT,'creation state mismatch'); END;
CREATE TRIGGER IF NOT EXISTS event_OrderLine_chronology BEFORE INSERT ON EventLog
            WHEN NEW."OrderLine_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "OrderLine_id"=NEW."OrderLine_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE TRIGGER IF NOT EXISTS event_OrderLine_stateless BEFORE INSERT ON EventLog
                WHEN NEW."OrderLine_id" IS NOT NULL AND (NEW.event_type='STATE_CHANGED' OR NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT NULL)
                BEGIN SELECT RAISE(ABORT,'stateless entity'); END;
CREATE TRIGGER IF NOT EXISTS event_ReturnRequest_chronology BEFORE INSERT ON EventLog
            WHEN NEW."ReturnRequest_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "ReturnRequest_id"=NEW."ReturnRequest_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE UNIQUE INDEX IF NOT EXISTS event_ReturnRequest_one_creation
                ON EventLog("ReturnRequest_id") WHERE event_type='CREATED';
CREATE TRIGGER IF NOT EXISTS event_ReturnRequest_creation BEFORE INSERT ON EventLog
                WHEN NEW."ReturnRequest_id" IS NOT NULL AND NEW.event_type='CREATED'
                AND (NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT (SELECT state FROM "ReturnRequest" WHERE id=NEW."ReturnRequest_id"))
                BEGIN SELECT RAISE(ABORT,'creation state mismatch'); END;
CREATE TRIGGER IF NOT EXISTS event_ReturnLine_chronology BEFORE INSERT ON EventLog
            WHEN NEW."ReturnLine_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "ReturnLine_id"=NEW."ReturnLine_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE UNIQUE INDEX IF NOT EXISTS event_ReturnLine_one_creation
                ON EventLog("ReturnLine_id") WHERE event_type='CREATED';
CREATE TRIGGER IF NOT EXISTS event_ReturnLine_creation BEFORE INSERT ON EventLog
                WHEN NEW."ReturnLine_id" IS NOT NULL AND NEW.event_type='CREATED'
                AND (NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT (SELECT state FROM "ReturnLine" WHERE id=NEW."ReturnLine_id"))
                BEGIN SELECT RAISE(ABORT,'creation state mismatch'); END;
CREATE TRIGGER IF NOT EXISTS event_ReturnAuthorization_chronology BEFORE INSERT ON EventLog
            WHEN NEW."ReturnAuthorization_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "ReturnAuthorization_id"=NEW."ReturnAuthorization_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE UNIQUE INDEX IF NOT EXISTS event_ReturnAuthorization_one_creation
                ON EventLog("ReturnAuthorization_id") WHERE event_type='CREATED';
CREATE TRIGGER IF NOT EXISTS event_ReturnAuthorization_creation BEFORE INSERT ON EventLog
                WHEN NEW."ReturnAuthorization_id" IS NOT NULL AND NEW.event_type='CREATED'
                AND (NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT (SELECT state FROM "ReturnAuthorization" WHERE id=NEW."ReturnAuthorization_id"))
                BEGIN SELECT RAISE(ABORT,'creation state mismatch'); END;
CREATE TRIGGER IF NOT EXISTS event_AuthorizationLine_chronology BEFORE INSERT ON EventLog
            WHEN NEW."AuthorizationLine_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "AuthorizationLine_id"=NEW."AuthorizationLine_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE TRIGGER IF NOT EXISTS event_AuthorizationLine_stateless BEFORE INSERT ON EventLog
                WHEN NEW."AuthorizationLine_id" IS NOT NULL AND (NEW.event_type='STATE_CHANGED' OR NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT NULL)
                BEGIN SELECT RAISE(ABORT,'stateless entity'); END;
CREATE TRIGGER IF NOT EXISTS event_ReturnShipment_chronology BEFORE INSERT ON EventLog
            WHEN NEW."ReturnShipment_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "ReturnShipment_id"=NEW."ReturnShipment_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE UNIQUE INDEX IF NOT EXISTS event_ReturnShipment_one_creation
                ON EventLog("ReturnShipment_id") WHERE event_type='CREATED';
CREATE TRIGGER IF NOT EXISTS event_ReturnShipment_creation BEFORE INSERT ON EventLog
                WHEN NEW."ReturnShipment_id" IS NOT NULL AND NEW.event_type='CREATED'
                AND (NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT (SELECT state FROM "ReturnShipment" WHERE id=NEW."ReturnShipment_id"))
                BEGIN SELECT RAISE(ABORT,'creation state mismatch'); END;
CREATE TRIGGER IF NOT EXISTS event_ShipmentLine_chronology BEFORE INSERT ON EventLog
            WHEN NEW."ShipmentLine_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "ShipmentLine_id"=NEW."ShipmentLine_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE TRIGGER IF NOT EXISTS event_ShipmentLine_stateless BEFORE INSERT ON EventLog
                WHEN NEW."ShipmentLine_id" IS NOT NULL AND (NEW.event_type='STATE_CHANGED' OR NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT NULL)
                BEGIN SELECT RAISE(ABORT,'stateless entity'); END;
CREATE TRIGGER IF NOT EXISTS event_Inspection_chronology BEFORE INSERT ON EventLog
            WHEN NEW."Inspection_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "Inspection_id"=NEW."Inspection_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE UNIQUE INDEX IF NOT EXISTS event_Inspection_one_creation
                ON EventLog("Inspection_id") WHERE event_type='CREATED';
CREATE TRIGGER IF NOT EXISTS event_Inspection_creation BEFORE INSERT ON EventLog
                WHEN NEW."Inspection_id" IS NOT NULL AND NEW.event_type='CREATED'
                AND (NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT (SELECT state FROM "Inspection" WHERE id=NEW."Inspection_id"))
                BEGIN SELECT RAISE(ABORT,'creation state mismatch'); END;
CREATE TRIGGER IF NOT EXISTS event_RefundObligation_chronology BEFORE INSERT ON EventLog
            WHEN NEW."RefundObligation_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "RefundObligation_id"=NEW."RefundObligation_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE TRIGGER IF NOT EXISTS event_RefundObligation_stateless BEFORE INSERT ON EventLog
                WHEN NEW."RefundObligation_id" IS NOT NULL AND (NEW.event_type='STATE_CHANGED' OR NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT NULL)
                BEGIN SELECT RAISE(ABORT,'stateless entity'); END;
CREATE TRIGGER IF NOT EXISTS event_Refund_chronology BEFORE INSERT ON EventLog
            WHEN NEW."Refund_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "Refund_id"=NEW."Refund_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE UNIQUE INDEX IF NOT EXISTS event_Refund_one_creation
                ON EventLog("Refund_id") WHERE event_type='CREATED';
CREATE TRIGGER IF NOT EXISTS event_Refund_creation BEFORE INSERT ON EventLog
                WHEN NEW."Refund_id" IS NOT NULL AND NEW.event_type='CREATED'
                AND (NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT (SELECT state FROM "Refund" WHERE id=NEW."Refund_id"))
                BEGIN SELECT RAISE(ABORT,'creation state mismatch'); END;
CREATE TRIGGER IF NOT EXISTS event_InventoryDisposition_chronology BEFORE INSERT ON EventLog
            WHEN NEW."InventoryDisposition_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "InventoryDisposition_id"=NEW."InventoryDisposition_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE UNIQUE INDEX IF NOT EXISTS event_InventoryDisposition_one_creation
                ON EventLog("InventoryDisposition_id") WHERE event_type='CREATED';
CREATE TRIGGER IF NOT EXISTS event_InventoryDisposition_creation BEFORE INSERT ON EventLog
                WHEN NEW."InventoryDisposition_id" IS NOT NULL AND NEW.event_type='CREATED'
                AND (NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT (SELECT state FROM "InventoryDisposition" WHERE id=NEW."InventoryDisposition_id"))
                BEGIN SELECT RAISE(ABORT,'creation state mismatch'); END;
CREATE TRIGGER IF NOT EXISTS event_InventoryMovement_chronology BEFORE INSERT ON EventLog
            WHEN NEW."InventoryMovement_id" IS NOT NULL AND EXISTS(SELECT 1 FROM EventLog WHERE "InventoryMovement_id"=NEW."InventoryMovement_id" AND occurred_at>NEW.occurred_at)
            BEGIN SELECT RAISE(ABORT,'event time precedes history'); END;
CREATE TRIGGER IF NOT EXISTS event_InventoryMovement_stateless BEFORE INSERT ON EventLog
                WHEN NEW."InventoryMovement_id" IS NOT NULL AND (NEW.event_type='STATE_CHANGED' OR NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT NULL)
                BEGIN SELECT RAISE(ABORT,'stateless entity'); END;
CREATE TRIGGER IF NOT EXISTS observation_has_no_state BEFORE INSERT ON EventLog
        WHEN NEW.event_type='OBSERVED' AND (NEW.previous_state IS NOT NULL OR NEW.new_state IS NOT NULL)
        BEGIN SELECT RAISE(ABORT,'observation cannot change state'); END;
CREATE TRIGGER IF NOT EXISTS return_line_same_order_INSERT BEFORE INSERT ON "ReturnLine"
        WHEN NOT (EXISTS(
        SELECT 1 FROM ReturnRequest r JOIN OrderLine o ON o.order_id=r.order_id
        WHERE r.id=NEW.request_id AND o.id=NEW.order_line_id)) BEGIN SELECT RAISE(ABORT,'return_line_same_order'); END;
CREATE TRIGGER IF NOT EXISTS return_line_same_order_UPDATE BEFORE UPDATE ON "ReturnLine"
        WHEN NOT (EXISTS(
        SELECT 1 FROM ReturnRequest r JOIN OrderLine o ON o.order_id=r.order_id
        WHERE r.id=NEW.request_id AND o.id=NEW.order_line_id)) BEGIN SELECT RAISE(ABORT,'return_line_same_order'); END;
CREATE TRIGGER IF NOT EXISTS authorization_same_request_INSERT BEFORE INSERT ON "AuthorizationLine"
        WHEN NOT (EXISTS(
        SELECT 1 FROM ReturnAuthorization a JOIN ReturnLine l ON l.request_id=a.request_id
        WHERE a.id=NEW.authorization_id AND l.id=NEW.return_line_id AND NEW.approved_quantity<=l.requested_quantity)) BEGIN SELECT RAISE(ABORT,'authorization_same_request'); END;
CREATE TRIGGER IF NOT EXISTS authorization_same_request_UPDATE BEFORE UPDATE ON "AuthorizationLine"
        WHEN NOT (EXISTS(
        SELECT 1 FROM ReturnAuthorization a JOIN ReturnLine l ON l.request_id=a.request_id
        WHERE a.id=NEW.authorization_id AND l.id=NEW.return_line_id AND NEW.approved_quantity<=l.requested_quantity)) BEGIN SELECT RAISE(ABORT,'authorization_same_request'); END;
CREATE TRIGGER IF NOT EXISTS shipment_quantity_limit_INSERT BEFORE INSERT ON "ShipmentLine"
        WHEN NOT (EXISTS(
        SELECT 1 FROM AuthorizationLine a WHERE a.id=NEW.authorization_line_id
        AND NEW.shipped_quantity+COALESCE((SELECT SUM(shipped_quantity) FROM ShipmentLine
        WHERE authorization_line_id=a.id AND id<>NEW.id),0)<=a.approved_quantity)) BEGIN SELECT RAISE(ABORT,'shipment_quantity_limit'); END;
CREATE TRIGGER IF NOT EXISTS shipment_quantity_limit_UPDATE BEFORE UPDATE ON "ShipmentLine"
        WHEN NOT (EXISTS(
        SELECT 1 FROM AuthorizationLine a WHERE a.id=NEW.authorization_line_id
        AND NEW.shipped_quantity+COALESCE((SELECT SUM(shipped_quantity) FROM ShipmentLine
        WHERE authorization_line_id=a.id AND id<>NEW.id),0)<=a.approved_quantity)) BEGIN SELECT RAISE(ABORT,'shipment_quantity_limit'); END;
CREATE TRIGGER IF NOT EXISTS inspection_received_limit_INSERT BEFORE INSERT ON "Inspection"
        WHEN NOT (EXISTS(
        SELECT 1 FROM ShipmentLine l JOIN ReturnShipment s ON s.id=l.shipment_id
        WHERE l.id=NEW.shipment_line_id AND s.delivered_at IS NOT NULL AND NEW.inspected_at>=s.delivered_at
        AND NEW.inspected_quantity+COALESCE((SELECT SUM(inspected_quantity) FROM Inspection
        WHERE shipment_line_id=l.id AND id<>NEW.id),0)<=l.received_quantity)) BEGIN SELECT RAISE(ABORT,'inspection_received_limit'); END;
CREATE TRIGGER IF NOT EXISTS inspection_received_limit_UPDATE BEFORE UPDATE ON "Inspection"
        WHEN NOT (EXISTS(
        SELECT 1 FROM ShipmentLine l JOIN ReturnShipment s ON s.id=l.shipment_id
        WHERE l.id=NEW.shipment_line_id AND s.delivered_at IS NOT NULL AND NEW.inspected_at>=s.delivered_at
        AND NEW.inspected_quantity+COALESCE((SELECT SUM(inspected_quantity) FROM Inspection
        WHERE shipment_line_id=l.id AND id<>NEW.id),0)<=l.received_quantity)) BEGIN SELECT RAISE(ABORT,'inspection_received_limit'); END;
CREATE TRIGGER IF NOT EXISTS RefundObligation_inspection_link_INSERT BEFORE INSERT ON "RefundObligation"
        WHEN NOT (NEW.inspection_id IS NULL OR EXISTS(SELECT 1 FROM Inspection i JOIN ShipmentLine s ON s.id=i.shipment_line_id
        JOIN AuthorizationLine a ON a.id=s.authorization_line_id
        WHERE i.id=NEW.inspection_id AND a.return_line_id=NEW.return_line_id)) BEGIN SELECT RAISE(ABORT,'RefundObligation_inspection_link'); END;
CREATE TRIGGER IF NOT EXISTS RefundObligation_inspection_link_UPDATE BEFORE UPDATE ON "RefundObligation"
        WHEN NOT (NEW.inspection_id IS NULL OR EXISTS(SELECT 1 FROM Inspection i JOIN ShipmentLine s ON s.id=i.shipment_line_id
        JOIN AuthorizationLine a ON a.id=s.authorization_line_id
        WHERE i.id=NEW.inspection_id AND a.return_line_id=NEW.return_line_id)) BEGIN SELECT RAISE(ABORT,'RefundObligation_inspection_link'); END;
CREATE TRIGGER IF NOT EXISTS InventoryDisposition_inspection_link_INSERT BEFORE INSERT ON "InventoryDisposition"
        WHEN NOT (NEW.inspection_id IS NULL OR EXISTS(SELECT 1 FROM Inspection i JOIN ShipmentLine s ON s.id=i.shipment_line_id
        JOIN AuthorizationLine a ON a.id=s.authorization_line_id
        WHERE i.id=NEW.inspection_id AND a.return_line_id=NEW.return_line_id)) BEGIN SELECT RAISE(ABORT,'InventoryDisposition_inspection_link'); END;
CREATE TRIGGER IF NOT EXISTS InventoryDisposition_inspection_link_UPDATE BEFORE UPDATE ON "InventoryDisposition"
        WHEN NOT (NEW.inspection_id IS NULL OR EXISTS(SELECT 1 FROM Inspection i JOIN ShipmentLine s ON s.id=i.shipment_line_id
        JOIN AuthorizationLine a ON a.id=s.authorization_line_id
        WHERE i.id=NEW.inspection_id AND a.return_line_id=NEW.return_line_id)) BEGIN SELECT RAISE(ABORT,'InventoryDisposition_inspection_link'); END;
CREATE TRIGGER IF NOT EXISTS refund_success_guard_INSERT BEFORE INSERT ON "Refund"
        WHEN NOT (NEW.state<>'SUCCEEDED' OR EXISTS(
        SELECT 1 FROM RefundObligation o JOIN Inspection i ON i.id=o.inspection_id
        JOIN ReturnLine l ON l.id=o.return_line_id JOIN OrderLine ol ON ol.id=l.order_line_id
        WHERE o.id=NEW.obligation_id AND i.state='FINALIZED' AND NEW.attempted_at>=i.inspected_at
        AND NEW.paid_minor+COALESCE((SELECT SUM(paid_minor) FROM Refund WHERE obligation_id=o.id AND id<>NEW.id),0)<=o.entitlement_minor
        AND NEW.paid_minor+COALESCE((SELECT SUM(r.paid_minor) FROM Refund r JOIN RefundObligation b ON b.id=r.obligation_id
        JOIN ReturnLine rl ON rl.id=b.return_line_id WHERE rl.order_line_id=ol.id AND r.id<>NEW.id),0)<=ol.paid_minor)) BEGIN SELECT RAISE(ABORT,'refund_success_guard'); END;
CREATE TRIGGER IF NOT EXISTS refund_success_guard_UPDATE BEFORE UPDATE ON "Refund"
        WHEN NOT (NEW.state<>'SUCCEEDED' OR EXISTS(
        SELECT 1 FROM RefundObligation o JOIN Inspection i ON i.id=o.inspection_id
        JOIN ReturnLine l ON l.id=o.return_line_id JOIN OrderLine ol ON ol.id=l.order_line_id
        WHERE o.id=NEW.obligation_id AND i.state='FINALIZED' AND NEW.attempted_at>=i.inspected_at
        AND NEW.paid_minor+COALESCE((SELECT SUM(paid_minor) FROM Refund WHERE obligation_id=o.id AND id<>NEW.id),0)<=o.entitlement_minor
        AND NEW.paid_minor+COALESCE((SELECT SUM(r.paid_minor) FROM Refund r JOIN RefundObligation b ON b.id=r.obligation_id
        JOIN ReturnLine rl ON rl.id=b.return_line_id WHERE rl.order_line_id=ol.id AND r.id<>NEW.id),0)<=ol.paid_minor)) BEGIN SELECT RAISE(ABORT,'refund_success_guard'); END;
CREATE TRIGGER IF NOT EXISTS accepted_disposition_guard_INSERT BEFORE INSERT ON "InventoryDisposition"
        WHEN NOT (NEW.state<>'ACCEPTED' OR EXISTS(
        SELECT 1 FROM Inspection i WHERE i.id=NEW.inspection_id AND i.state='FINALIZED'
        AND NEW.decided_at>=i.inspected_at AND (NEW.action<>'RESTOCK' OR i.condition='SELLABLE')
        AND NEW.quantity+COALESCE((SELECT SUM(quantity) FROM InventoryDisposition WHERE inspection_id=i.id
        AND state='ACCEPTED' AND id<>NEW.id),0)<=i.inspected_quantity)) BEGIN SELECT RAISE(ABORT,'accepted_disposition_guard'); END;
CREATE TRIGGER IF NOT EXISTS accepted_disposition_guard_UPDATE BEFORE UPDATE ON "InventoryDisposition"
        WHEN NOT (NEW.state<>'ACCEPTED' OR EXISTS(
        SELECT 1 FROM Inspection i WHERE i.id=NEW.inspection_id AND i.state='FINALIZED'
        AND NEW.decided_at>=i.inspected_at AND (NEW.action<>'RESTOCK' OR i.condition='SELLABLE')
        AND NEW.quantity+COALESCE((SELECT SUM(quantity) FROM InventoryDisposition WHERE inspection_id=i.id
        AND state='ACCEPTED' AND id<>NEW.id),0)<=i.inspected_quantity)) BEGIN SELECT RAISE(ABORT,'accepted_disposition_guard'); END;
CREATE TRIGGER IF NOT EXISTS movement_requires_accepted_decision_INSERT BEFORE INSERT ON "InventoryMovement"
        WHEN NOT (EXISTS(
        SELECT 1 FROM InventoryDisposition d WHERE d.id=NEW.disposition_id AND d.state='ACCEPTED'
        AND NEW.quantity=d.quantity AND NEW.moved_at>=d.decided_at)) BEGIN SELECT RAISE(ABORT,'movement_requires_accepted_decision'); END;
CREATE TRIGGER IF NOT EXISTS movement_requires_accepted_decision_UPDATE BEFORE UPDATE ON "InventoryMovement"
        WHEN NOT (EXISTS(
        SELECT 1 FROM InventoryDisposition d WHERE d.id=NEW.disposition_id AND d.state='ACCEPTED'
        AND NEW.quantity=d.quantity AND NEW.moved_at>=d.decided_at)) BEGIN SELECT RAISE(ABORT,'movement_requires_accepted_decision'); END;
CREATE TRIGGER IF NOT EXISTS Refund_terminal_immutable BEFORE UPDATE ON Refund
            WHEN OLD.state IN ('SUCCEEDED','FAILED','REJECTED') BEGIN SELECT RAISE(ABORT,'terminal evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS Refund_no_delete BEFORE DELETE ON Refund
            BEGIN SELECT RAISE(ABORT,'audit evidence cannot be deleted'); END;
CREATE TRIGGER IF NOT EXISTS InventoryDisposition_terminal_immutable BEFORE UPDATE ON InventoryDisposition
            WHEN OLD.state IN ('ACCEPTED','REJECTED') BEGIN SELECT RAISE(ABORT,'terminal evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS InventoryDisposition_no_delete BEFORE DELETE ON InventoryDisposition
            BEGIN SELECT RAISE(ABORT,'audit evidence cannot be deleted'); END;
CREATE TRIGGER IF NOT EXISTS Inspection_terminal_immutable BEFORE UPDATE ON Inspection
            WHEN OLD.state='FINALIZED' BEGIN SELECT RAISE(ABORT,'terminal evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS Inspection_no_delete BEFORE DELETE ON Inspection
            BEGIN SELECT RAISE(ABORT,'audit evidence cannot be deleted'); END;
CREATE TRIGGER IF NOT EXISTS obligation_fixed_after_attempt BEFORE UPDATE ON RefundObligation
        WHEN EXISTS(SELECT 1 FROM Refund WHERE obligation_id=OLD.id)
        BEGIN SELECT RAISE(ABORT,'attempted obligation is immutable'); END;
CREATE TRIGGER IF NOT EXISTS OrderLine_freeze_referenced_evidence BEFORE UPDATE ON "OrderLine"
            WHEN EXISTS(SELECT 1 FROM ReturnLine WHERE order_line_id=OLD.id) BEGIN SELECT RAISE(ABORT,'referenced evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS ShipmentLine_freeze_referenced_evidence BEFORE UPDATE ON "ShipmentLine"
            WHEN EXISTS(SELECT 1 FROM Inspection WHERE shipment_line_id=OLD.id) BEGIN SELECT RAISE(ABORT,'referenced evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS AuthorizationLine_freeze_referenced_evidence BEFORE UPDATE ON "AuthorizationLine"
            WHEN EXISTS(SELECT 1 FROM ShipmentLine WHERE authorization_line_id=OLD.id) BEGIN SELECT RAISE(ABORT,'referenced evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS ReturnPolicy_freeze_referenced_evidence BEFORE UPDATE ON "ReturnPolicy"
            WHEN EXISTS(SELECT 1 FROM ReturnRequest WHERE policy_id=OLD.id) BEGIN SELECT RAISE(ABORT,'referenced evidence is immutable'); END;
