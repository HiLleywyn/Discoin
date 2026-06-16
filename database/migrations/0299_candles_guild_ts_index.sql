-- 0299_candles_guild_ts_index.sql
-- The batched TWAP query (get_all_twaps) filters price_candles by
-- (guild_id, ts) across ALL symbols at once. The existing
-- idx_candles_ts (guild_id, symbol, ts DESC) can't serve that filter
-- efficiently because ts sits behind symbol. Without this index the
-- drift loop's per-tick TWAP query degrades as candle history grows
-- until it exceeds the 30s command timeout (production incident).

CREATE INDEX IF NOT EXISTS idx_candles_guild_ts
    ON price_candles (guild_id, ts DESC);
