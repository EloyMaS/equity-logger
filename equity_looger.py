# equity_logger.py
import os, time, csv
from datetime import datetime, timezone, timedelta
import ccxt

# ====== ENV ======
EXCHANGE_ID = os.getenv("EXCHANGE_ID", "binance")
SYMBOL = os.getenv("SYMBOL", "PEPEUSDC")   # match Binance isolated margin symbols (no slash)
MARGIN_MODE = os.getenv("MARGIN_MODE", "isolated")

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

CSV_FILE = "equity.csv"

# ====== EXCHANGE ======
def build_exchange():
    opts = {
        "apiKey": API_KEY,
        "secret": API_SECRET,
        "enableRateLimit": True,
        "options": {
            "defaultType": "spot",
            "defaultMarginMode": MARGIN_MODE,
            "adjustForTimeDifference": True,
            "recvWindow": 1500,
        },
    }
    return getattr(ccxt, EXCHANGE_ID)(opts)

def fetch_nav(ex, symbol: str) -> float:
    """Return NAV for a given isolated margin pair, in quote currency (USDC)."""
    data = ex.sapi_get_margin_isolated_account()
    for asset in data.get("assets", []):
        if asset["symbol"] == symbol:
            quote_val = float(asset["quoteAsset"]["netAsset"])
            base_val  = float(asset["baseAsset"]["netAsset"])
            last_price = float(ex.fetch_ticker(symbol.replace("", "/"))["last"])
            return quote_val + base_val * last_price
    raise ValueError(f"{symbol} not found in isolated margin account")

def log_nav():
    ex = build_exchange()

    # init CSV with header
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as f:
            csv.writer(f).writerow(["timestamp", "symbol", "nav"])

    while True:
        try:
            nav = fetch_nav(ex, SYMBOL)
            ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            with open(CSV_FILE, "a", newline="") as f:
                csv.writer(f).writerow([ts, SYMBOL, nav])
            print(f"{ts} | {SYMBOL} NAV={nav}")
        except Exception as e:
            print("NAV update failed:", e)

        # calculate sleep until next top of hour
        now = datetime.now()
        next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
        sleep_secs = (next_hour - now).total_seconds()
        time.sleep(sleep_secs)

if __name__ == "__main__":
    log_nav()
