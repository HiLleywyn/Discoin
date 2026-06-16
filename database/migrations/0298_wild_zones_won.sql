-- 0298_wild_zones_won.sql
-- Track WHICH farming zones a player has won wild-buddy battles in, not
-- just how many battles. The "Habitat Hunter" achievement (win in 5
-- different zones) listens for the wild_zone_visited bus event with a
-- distinct-zone count; until now nothing recorded zones, so the badge
-- was unobtainable.

ALTER TABLE user_farming
    ADD COLUMN IF NOT EXISTS wild_zones_won TEXT[] NOT NULL DEFAULT '{}';
