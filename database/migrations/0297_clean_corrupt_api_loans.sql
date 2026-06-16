-- 0297_clean_corrupt_api_loans.sql
-- The v2 API lending endpoints used to write HUMAN-scale floats (e.g. 100.5)
-- straight into the raw NUMERIC(36,0) x 10**18 loan columns. The resulting
-- rows are economically worthless dust (outstanding < 0.000001 USD) but
-- still register as "an active loan", blocking those players from borrowing
-- at all. Refund the dust collateral and close the rows.
--
-- Threshold: 10**12 raw = 0.000001 USD. No legitimate loan is ever this
-- small (the bot enforces a minimum borrow far above one millionth of a
-- dollar); only corrupt API writes land in (0, 10**12).

BEGIN;

-- 1. Return dust collateral to the wallet
UPDATE users u
SET    wallet = u.wallet + l.collateral
FROM   loans l
WHERE  l.user_id  = u.user_id
  AND  l.guild_id = u.guild_id
  AND  l.outstanding > 0
  AND  l.outstanding < 1000000000000
  AND  l.collateral  > 0
  AND  l.collateral  < 1000000000000;

-- 2. Close the corrupt loans
UPDATE loans
SET    outstanding = 0, collateral = 0
WHERE  outstanding > 0
  AND  outstanding < 1000000000000
  AND  collateral  < 1000000000000;

COMMIT;
