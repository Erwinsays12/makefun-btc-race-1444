"""Regime-filtered 60-minute momentum bot for cbBTC/USDC.

Speaks agent-fun/bars-replay/v1 through the vendored shim in vendor/.
One asset, CBBTC, long only, starting from 1,000 USDC of paper money.

The idea, in one paragraph: one-minute cbBTC prices are noisy (about 7 bps
of standard deviation per minute) while a full round trip costs about 26 bps
in fees, slippage and pool impact, so trading every wiggle loses money.
What does persist in the dev window is the 60-minute trend: after the
trailing 60-minute return tops +60 bps, the next 60 minutes average about
+28 bps. This bot therefore trades rarely, only when the hourly trend is
strong, confirmed by the half-hour trend, and only while the price sits
above its 240-minute average (a longer-trend regime filter that keeps it
out of counter-trend bounces in a falling market). It rides the trend
until the hourly return turns clearly negative, then steps aside.

Entry (on a bar's close, filled at the next bar's open), full equity:
  - trailing 60-minute return above +45 bps, and
  - trailing 30-minute return above 0, and
  - the close above the trailing 240-bar simple moving average.
Exit (the whole position):
  - trailing 60-minute return below -40 bps.

Everything is integer arithmetic on the closes the harness has sent, so
the same bars always give the same orders: no clock, no network, no
randomness, no environment reads. Returns are looked up by time (the bar
closest to 60 / 30 minutes ago), so a missing minute degrades gracefully
instead of shifting the window; the moving average is over the last 240
closes the bot has seen. Orders carry a 100 bps slippage cap, far above
the ~10 bps of impact a full-size fill meets, so a fill is refused only
on a genuinely violent open.
"""

import os
import sys
from bisect import bisect_right

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
MINUTE_MS = 60_000
ENTER_RET60_BPS = 45
ENTER_RET30_BPS = 0
EXIT_RET60_BPS = -40
SMA_BARS = 240
MAX_SLIPPAGE_BPS = 100


class MomentumBot:
    """The strategy state: the closes seen so far, nothing else."""

    def __init__(self):
        # (close time ms, close price int) in the order the bars arrived.
        self.times = []
        self.closes = []

    def note_bar(self, bar):
        self.times.append(int(bar["t"]))
        self.closes.append(int(bar["c"]))

    def _close_at_or_before(self, when_ms):
        """The latest close at or before a time, or None when there is none."""
        i = bisect_right(self.times, when_ms) - 1
        return None if i < 0 else self.closes[i]

    def trailing_return_bps(self, now_ms, minutes):
        """The return in bps from the close `minutes` ago to the latest close."""
        ref = self._close_at_or_before(now_ms - minutes * MINUTE_MS)
        if ref is None or not self.closes:
            return None
        return (self.closes[-1] - ref) * 10_000 // ref

    def above_sma(self):
        """Whether the latest close sits above its trailing SMA_BARS average."""
        if len(self.closes) < SMA_BARS:
            return False
        window = self.closes[-SMA_BARS:]
        return self.closes[-1] * SMA_BARS > sum(window)


BOT = MomentumBot()


def on_batch(state, batch):
    bar = None
    for b in batch["bars"]:
        if b["symbol"] == SYMBOL:
            bar = b
            break
    if bar is None:
        # No CBBTC bar this minute: nothing new to decide on.
        return []
    # Record the bar even while warming up: warm-up bars are the bars
    # before the scored window, sent to build history from, and orders
    # decided on them would only be rejected.
    BOT.note_bar(bar)
    if state.warming_up:
        return []

    ret60 = BOT.trailing_return_bps(int(bar["t"]), 60)
    if ret60 is None:
        return []
    held = state.positions.get(SYMBOL)
    if held is not None:
        if ret60 < EXIT_RET60_BPS:
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []
    ret30 = BOT.trailing_return_bps(int(bar["t"]), 30)
    if ret30 is None:
        return []
    if (ret60 > ENTER_RET60_BPS and ret30 > ENTER_RET30_BPS
            and BOT.above_sma()):
        room = state.weight_room(SYMBOL)
        notional = state.cash if state.cash < room else room
        if notional >= int(state.hello["fees"]["min_notional_quote_units"]):
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": notional,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    return []


makefun_bars.run(on_batch)
