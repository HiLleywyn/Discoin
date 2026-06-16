-- 0296_remove_sun_savings.sql
-- SUN savings do not exist: SUN is a tradeable network token, not a
-- stablecoin, and must never sit in the savings vault. Refund any
-- remaining SUN savings deposits to CeFi holdings so no player loses
-- funds, then delete the rows. The savings system is USD-only from now on.

BEGIN;

-- 1. SUN savings -> CeFi holdings (crypto_holdings table)
INSERT INTO crypto_holdings (user_id, guild_id, symbol, amount)
SELECT s.user_id, s.guild_id, 'SUN', s.amount
FROM   savings_deposits s
WHERE  s.symbol = 'SUN'
  AND  s.amount > 0
ON CONFLICT (user_id, guild_id, symbol)
DO UPDATE SET amount = crypto_holdings.amount + EXCLUDED.amount;

-- 2. Remove all non-USD savings rows (refunded above or zero-balance)
DELETE FROM savings_deposits
WHERE  symbol <> 'USD';

COMMIT;
