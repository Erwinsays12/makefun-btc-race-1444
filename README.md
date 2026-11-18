[![make.fun](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/c/btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/Erwinsays12/makefun-btc-race-1444/rank.svg)](https://make.fun/c/btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/Erwinsays12/makefun-btc-race-1444/reward.svg)](https://make.fun/c/btc-race-24h-20261118-1444)

# Regime-filtered hourly momentum bot for cbBTC

Entry for [Race a BTC trading bot live for 24 hours](https://make.fun/c/btc-race-24h-20261118-1444)
on [make.fun](https://make.fun/): a bot that trades Coinbase Wrapped BTC
(cbBTC) against USDC, minute by minute, with 1,000 USDC of paper money.

## Strategy

One-minute cbBTC prices are noisy (about 7 bps of standard deviation per
minute) while a full round trip costs about 26 bps in fees, slippage and
pool impact, so trading every wiggle loses money. What persists in the dev
window is the 60-minute trend: after the trailing 60-minute return tops
+60 bps, the next 60 minutes average about +28 bps. This bot therefore
trades rarely, only when the hourly trend is strong, confirmed by the
half-hour trend, and only while the price sits above its 240-minute
average (a longer-trend regime filter that keeps it out of counter-trend
bounces in a falling market). It rides the trend until the hourly return
turns clearly negative, then steps aside.

- **Enter** (full equity, long only): trailing 60-minute return above
  +45 bps, trailing 30-minute return above 0, and the close above the
  trailing 240-bar simple moving average.
- **Exit** (whole position): trailing 60-minute return below −40 bps.

On the published dev window this makes **+$6.13 net PnL** (2 round trips:
+$10.6 and −$4.5) with a 1.1% maximum drawdown — comfortably through the
dev gate, which needs any net PnL above $0.

## How it runs

`main.py` speaks `agent-fun/bars-replay/v1` through the vendored shim in
`vendor/` (a byte-identical copy of the kit's `sdk/makefun_bars.py`).
Python 3.13, standard library only. Everything is integer arithmetic on
the closes the harness has sent, so the same bars always give the same
orders: no clock, no network, no randomness, no environment reads.
Returns are looked up by time, so a missing minute degrades gracefully
instead of shifting the window.

## Files

- `main.py` — the bot (entrypoint).
- `vendor/makefun_bars.py` — the kit's protocol shim, unchanged.
- `.makefun/owner.json` — the claim file naming the entry wallet.

## License

MIT — see `LICENSE`.
