-- Specification query for the planned DuckDB canonical procurement table.
-- Not executed by the foundation CLI. NULL is unknown, not a zero or one bid.
SELECT record_id, buyer_id, supplier_id, bid_count
FROM procurement_records
WHERE bid_count = 1;
