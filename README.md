<p align="center">
  <img src="images/banner.png" alt="Discoin" width="600" />
</p>

# Discoin

A Discord economy bot with a simulated crypto market, mining, staking, AMM liquidity pools, lending, smart contracts, and a web dashboard. Prices drift continuously via Geometric Brownian Motion, AI market makers trade automatically, and all on-chain transactions are bundled into ledger blocks every 30 minutes.

---

## Features

- **Crypto market**  -  40 built-in tokens across 12 networks  -  four crypto-style chains (Moneta, Sun, Arcadia, Discoin) plus eight themed gameplay networks (Moon, Lure, Crypt, Buddy, Harvest, Forge, Gamba, Sage). Crypto-style prices drift in real time via GBM.
- **Trading**  -  `.buy` / `.sell` for network coins and stablecoins; `.swap` for any token pair through AMM liquidity pools
- **Staking**  -  stake network tokens with player-run validators, earn hourly yield, risk slashing events
- **Mining**  -  buy GPU/ASIC rigs, mine SUN or MTA in solo/pool/group mode with Moneta-style difficulty retargeting
- **Moons & Moon Network**  -  native yield token. Stake group tokens to earn MOON (Lunar Mint); stake MOON to earn DSD from Moon Network trade revenue (Moon Pool).
- **Lending**  -  borrow USD against crypto collateral at up to 65% LTV; automatic liquidation at 80% LTV
- **Savings**  -  deposit USD or crypto to earn variable interest (Vantor V2-style utilization model)
- **Smart contracts**  -  deploy limit orders, escrow, and other on-chain logic via `.contract`
- **Gambling**  -  coinflip, dice, blackjack, slots, roulette with leverage up to 10x
- **DeFi wallets**  -  create network-scoped wallets, withdraw tokens from CeFi to DeFi, send between wallets
- **Shop & items**  -  Sunstone, Lockstone, Vaultstone (leveled items); Charms (timed buffs)
- **PoS validators**  -  players run their own validators, process mempool actions, earn gas fees; delegation system
- **AI moderation**  -  automatic scam/phishing detection; offending messages deleted and users timed out
- **Transaction explorer**  -  every action produces a hash; 30-min chain blocks with full tx history across every network
- **REST API + web dashboard**  -  Discord OAuth login, 2FA (TOTP), live candlestick charts, interactive trading, portfolio management, leaderboard, pool stats, contract browser, admin panel

---

## Multi-tenant / Premium

Discoin runs as a **single shared bot** that any server can invite. Trading,
gambling, bank, profile, jobs, and basic buddy management are **free everywhere**.
Cost-heavy features are gated behind a per-guild premium subscription paid via
PayPal:

- **Free**  -  trading, gambling, bank, work/daily/jobs, profile, drops, basic
  buddy commands (hatch, rename, storage, BUD economy, leaderboard, shop, staking)
- **Premium**  -  AI (`,ask`, `,disco`, AI replies/mentions), fishing, farming,
  crafting, delves, expeditions, buddy battles & arena, buddy breeding/eggs,
  buddy auction house, `,buddy talk`

Server admins run `,premium info` to see plans and `,premium subscribe` to get
a PayPal approval link. Once payment clears, a signature-verified webhook at
`/api/v2/paypal/webhook` flips premium on for everyone in that server.

The host server (set `HOST_GUILD_ID` in `.env`) is **auto-unlocked** with no DB
row required, so the operator's home server stays fully unlocked without paying.
The bot owner (`BOT_OWNER_ID`) can also manually grant premium to any guild via
`,admin premium grant <guild_id> [days]`.

See `.env.example` for all PayPal / premium settings.

---

## Quick Start (Docker)

Docker is the recommended way to run Discoin. The React frontend is built automatically inside the image  -  no Node.js required on the host.

```bash
git clone https://github.com/HiLleywyn/Discoin.git
cd Discoin
cp .env.example .env        # fill in your values
docker compose up -d --build
```

Dashboard: `http://localhost:8080/dashboard`
Health check: `http://localhost:8080/health`

---

## Manual Setup

**Requirements:** Python 3.11+, Node.js 18+ (for dashboard), a Discord bot token, [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

```bash
git clone https://github.com/HiLleywyn/Discoin.git
cd Discoin
uv pip install --system -r requirements.txt
uv pip install --system "playwright>=1.40.0"
playwright install chromium
playwright install-deps chromium
cp .env.example .env        # fill in your values
python main.py
```

> Playwright + Chromium are required for the `,trade chart` command (~500MB).
> The Docker image installs them in a dedicated layer ahead of `requirements.txt`,
> so bumping a Python dep no longer re-downloads Chromium on every rebuild.

To build the dashboard separately (served at `/dashboard`):

```bash
cd frontend
npm install && npm run build
```

> If you skip the dashboard build, the bot and API still work  -  only the web UI is missing.

---

## Discord Developer Portal Setup

### 1. Create the application

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications) → **New Application**
2. Left sidebar → **Bot** → **Add Bot**
3. Under **Token** → **Reset Token** → copy it → set `DISCORD_TOKEN=` in your `.env`

### 2. Enable OAuth2 for the dashboard

The dashboard uses Discord OAuth so users log in with their Discord account and pick a server  -  no manual Guild ID entry needed.

1. Left sidebar → **OAuth2** → **General**
2. Copy **Client ID** → set `DISCORD_CLIENT_ID=` in your `.env`
3. Copy **Client Secret** → set `DISCORD_CLIENT_SECRET=` in your `.env`
4. Under **Redirects** → **Add Redirect** → enter your callback URL:
   - Local dev: `http://localhost:8080/api/auth/callback`
   - Production: `https://your-domain.com/api/auth/callback`
5. Set `DISCORD_REDIRECT_URI=` in your `.env` to the **exact same URL** you entered above
6. Generate a JWT signing secret: `openssl rand -hex 32` → set `JWT_SECRET=`

> Without these, clicking "Login with Discord" on the dashboard will show an error.

### 2. Enable Privileged Gateway Intents

Still on the **Bot** page, scroll to **Privileged Gateway Intents** and enable all three:

| Intent | Why it's needed |
|---|---|
| ✅ **Presence Intent** | Bot activity status |
| ✅ **Server Members Intent** | Member cache for scam timeouts, guild-aware features |
| ✅ **Message Content Intent** | Reading message text for commands and scam detection |

### 3. Invite the bot with correct permissions

Left sidebar → **OAuth2** → **URL Generator**

**Scopes:** `bot`, `applications.commands`

**Bot Permissions:**

| Permission | Why it's needed |
|---|---|
| View Channels | Read channels to post into them |
| Send Messages | Post command responses and feeds |
| Send Messages in Threads | Post into thread-based feed channels |
| Embed Links | Rich embed responses |
| Attach Files | Chart image uploads |
| Read Message History | Context for AI replies and fuzzy matching |
| Add Reactions | Drop claim buttons and interactive UIs |
| Use External Emojis | Token/network emojis |
| Manage Messages | Delete scam messages (auto-mod) |
| Moderate Members | Timeout users flagged by AI scam detection |
| Manage Webhooks | Market-maker bot webhook for the trade feed |

Copy the generated URL → open in browser → invite to your server.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values. All variables are optional unless marked required.

| Variable | Required | Default | Description |
|---|---|---|---|
| `DISCORD_TOKEN` | ✅ |  -  | Your bot token |
| `PREFIX` | | `$` | Command prefix (e.g. `.` → `.balance`) |
| `DATABASE_URL` | ✅ | `postgresql://discoin:discoin@localhost:5432/discoin` | PostgreSQL connection string for the bot database. |
| `REDIS_URL` | | `redis://localhost:6379` | Redis connection string for the event bus and API pub/sub. Set automatically by Docker Compose. |
| `TX_SALT` | | `econbot-default-salt` | Salt for transaction hash generation. **Set this before first run  -  changing it later breaks all existing tx hashes.** Use `openssl rand -hex 32`. |
| `SLASH_GUILD_ID` | |  -  | Guild ID for instant slash command sync during dev. Leave blank for global sync in production. |
| `API_PORT` | | `8080` | Port for the web dashboard and REST API |
| `API_KEY` | |  -  | Legacy admin API key. Use `openssl rand -hex 32`. Leave blank to disable. |
| `DASHBOARD_URL` | |  -  | Public URL of your dashboard (used in Discord embeds, e.g. `https://discoin.example.com`) |
| `DISCORD_CLIENT_ID` | ✅ |  -  | OAuth2 Client ID from the Discord Developer Portal. Required for dashboard login. |
| `DISCORD_CLIENT_SECRET` | ✅ |  -  | OAuth2 Client Secret. Treat like a password. Required for dashboard login. |
| `DISCORD_REDIRECT_URI` | ✅ | `http://localhost:8080/api/auth/callback` | Must match the redirect URL added in the Discord Developer Portal exactly. |
| `JWT_SECRET` | ✅ |  -  | Secret used to sign dashboard session tokens. Use `openssl rand -hex 32`. |
| `JWT_EXPIRE_SECONDS` | | `604800` | Dashboard session length in seconds (default: 7 days). |
| `OPENROUTER_API_KEY` | |  -  | API key from [openrouter.ai](https://openrouter.ai). Leave blank to disable all AI features. |
| `OPENROUTER_MODEL` | | `openrouter/hunter-alpha` | AI model to use. See [openrouter.ai/models](https://openrouter.ai/models). |
| `AI_MM_ENABLED` | | `1` | AI market maker bot (auto-trades tokens) |
| `AI_CHAT_ENABLED` | | `1` | `.ask` command for users to chat with AI |
| `AI_COMMENTARY_ENABLED` | | `1` | AI market commentary after large price moves |
| `AI_FLAVOR_ENABLED` | | `0` | AI flavor text on `.work` responses (disabled by default  -  can be slow) |
| `AI_EVENTS_ENABLED` | | `1` | AI narration of notable trade events |
| `STARTING_BALANCE` | | `1000` | USD given to new users on first command |
| `DAILY_AMOUNT` | | `1000` | Base `.daily` reward |
| `WORK_COOLDOWN` | | `900` | Seconds between `.work` uses (15 min) |
| `AUTO_DROP_INTERVAL` | | `1800` | Seconds between automatic money drops (30 min) |
| `DROP_MIN` / `DROP_MAX` | | `100` / `2000` | Random drop value range (USD) |
| `MAX_BET` | | `500000` | Maximum bet on any gambling command |
| `CHAIN_BLOCK_INTERVAL` | | `1800` | Seconds between automatic chain block seals (30 min) |
| `AUTO_SEED_POOLS` | | `false` | Auto-seed all AMM pools with liquidity on startup |
| `POOL_SEED_STABLECOIN` | | `500000` | Stablecoin-side depth per pool when auto-seeding |
| `BACKUP_INTERVAL_HOURS` | | `6` | How often automatic DB backups run (hours) |
| `BACKUP_KEEP` | | `7` | Number of backup files to retain before rotating |
| `WALLET_PLATFORM_FEE_PCT` | | `0.002` | Platform fee on trades/withdrawals (decimal  -  `0.002` = 0.2%) |
| `WALLET_PLATFORM_FEE_MIN` | | `0.10` | Minimum platform fee in USD |
| `WALLET_PLATFORM_FEE_MAX` | | `20.00` | Maximum platform fee in USD |
| `HASHSTONE_XP_RATE` | | `40.0` | XP per (hashrate share × block found) for Hashstone levelling |
| `DEBUG` | | `false` | Enables `.admin log` and other debug commands. **Keep false in production.** |

---

## First-Time Server Setup

Once the bot is in your server, run these as a server admin (requires **Manage Server** permission):

```
.admin setup
```

Then assign feed channels. Each feed type can point to any text channel or thread:

```
.admin setchannel trade       #trade-feed
.admin setchannel crypto      #crypto-feed
.admin setchannel validators  #validator-feed
.admin setchannel staking     #staking-feed
.admin setchannel mine        #mining-feed
.admin setchannel pools       #pools-feed
.admin setchannel gambling    #gambling-feed
.admin setchannel drops       #drops-log
.admin setchannel dropsspawn  #drops          ← where drop messages appear for users to claim
.admin setchannel job         #jobs-feed
.admin setchannel contracts   #contracts-feed
.admin setchannel wallet      #wallet-feed
.admin setchannel error       #bot-errors
```

Or send everything to one channel:

```
.admin setchannel all #economy
```

### Optional: AI scam detection

```
.admin scam on
.admin scam channel #mod-alerts
.admin scam timeout 10          ← minutes (0 = no timeout, just delete)
```

Requires `OPENROUTER_API_KEY` to be set. Mods (anyone with **Manage Messages**) are never flagged.

### Optional: pool auto-seed

Set `AUTO_SEED_POOLS=true` in your `.env` before first run to pre-seed all AMM pools with `$500k` liquidity so users can trade immediately.

---

## Commands

Run `.help` in Discord for a full interactive reference. Quick overview:

| Category | Commands |
|---|---|
| Economy | `.balance`, `.deposit`, `.withdraw`, `.transfer`, `.daily`, `.work` |
| Trading | `.buy`, `.sell`, `.swap`, `.price`, `.portfolio` |
| Staking | `.stake`, `.unstake`, `.validators`, `.staking` |
| Mining | `.mine rigs/buy/sell/status/solo/pool/group` |
| Pools | `.pool list/create/info`, `.addlp`, `.removelp` |
| Lending | `.borrow`, `.repay`, `.loans` |
| Savings | `.deposit`, `.withdraw`, `.savings` |
| Contracts | `.contract deploy/call/info/list/events` |
| Gambling | `.coinflip`, `.dice`, `.blackjack`, `.slots`, `.roulette` |
| Groups | `.group create/join/leave/info/deposit/withdraw` |
| Wallets | `.wallet create/list/delete`, `.send` |
| Shop | `.shop`, `.use charm` |
| Explorer | `.block [network]`, `.txinfo <hash>` |
| Admin | `.admin give/take/setprice/addtoken/bundle/blockstatus/reseteconomy/log/...` |

---

## Networks & Tokens

Discoin ships 40 built-in tokens across 12 networks (plus group tokens and player-deployed tokens minted at runtime). The networks split into two groups.

**Crypto-style networks** behave like a simulated exchange: their coins carry a live price feed and trade for USD or through AMM pools.

| Network | Coins | Consensus |
|---|---|---|
| Moneta Chain | MTA | PoW (mineable) |
| Sun Network | SUN | PoW (mineable) |
| Arcadia Network | ARC, USDC, VTR, STR | PoS |
| Discoin Network | DSC, DSD, DSY, DEGEN, DRIP, DFUN | PoS |

USDC and DSD are the $1 stablecoins; ARC and DSC are the stakeable network coins; MTA and SUN are mined.

**Gameplay-system networks** each back a minigame, and their tokens are mostly earned by playing rather than bought directly.

| Network | Tokens | Powers |
|---|---|---|
| Moon Network | MOON, MMTA, MSUN | Moons yield system |
| Lure Network | LURE, REEL | Fishing |
| Crypt Network | RUNE, COPPER, SILVER, GOLD | Dungeons |
| Buddy Network | BUD, FREN, BBT | Buddies |
| Harvest Network | HRV, SEED | Farming |
| Forge Network | FORGE, INGOT, FGD | Crafting |
| Gamba Network | GBC and game tokens | Gambling |
| Sage Network | SAGE, EDU | Learn-and-earn quizzes |

```
.buy ARC 500           # buy ARC with USD
.buy USDC 1000         # buy a stablecoin with USD
.swap USDC VTR 500    # swap within the Arcadia Network
.sell SUN all          # sell back to USD
```

---

## Dashboard

Served at `http://localhost:<API_PORT>/dashboard`. Includes:

- **Login with Discord**  -  OAuth2 login, guild picker, optional TOTP-based 2FA
- **Interactive trading**  -  buy, sell, swap, stake, and manage savings directly from the dashboard
- **Portfolio**  -  full holdings breakdown with real-time valuations
- Live candlestick price charts (1m / 5m / 15m / 1h / 4h / 1d)
- Leaderboard and player profiles
- Validator overview and staking stats
- Mining rig stats and pool hashrate
- AMM pool stats and liquidity positions
- Transaction and block explorer
- Smart contract browser
- Savings & lending overview
- Admin panel (server admins get full access via Discord role check)

Requires `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI`, and `JWT_SECRET` to be set (see **Discord Developer Portal Setup** above).

---

## Configuration

Discoin uses a layered config system:

| Layer | Location | What it controls |
|---|---|---|
| `constants/` | 6 Python modules | Business rules: fees, rates, limits, colors, game rules |
| `core/config.py` | Single file | Tokens, networks, pools, env-loaded runtime settings |
| `security/config.py` | Single file | Abuse detection thresholds (overridable via `SEC_*` env vars) |
| `.env` | Environment | Secrets, connection strings, toggles |
| Database | `guild_settings` | Per-server prefix, channels, admin overrides |

Key values you may want to change:

| Setting | Location | Default | Description |
|---|---|---|---|
| `STARTING_BALANCE` | `.env` | 1000 | USD given to new users |
| `DAILY_AMOUNT` | `.env` | 1000 | Base `.daily` reward |
| `DEFAULT_SWAP_FEE` | `constants/trading.py` | 0.3% | AMM swap fee |
| `MAX_SLASH_COUNT` | `constants/validators.py` | 5 | Slashes before validator jail |
| `STAKE_LOCK_SECS` | `constants/validators.py` | 86400 | Stake lock period (24h) |
| `MINES_HOUSE_EDGE` | `constants/games.py` | 5% | House edge on mines |
| `POOL_SEED_STABLECOIN` | `.env` | $500,000 | Liquidity per side when auto-seeding |

See `core/config.py` for runtime settings (mining rigs, validator definitions, job tiers, lending parameters). See the [Configuration Reference](docs/getting-started/configuration.md) for the full picture.

---