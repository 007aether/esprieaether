import ccxt

def get_okx_market_data(symbol="BTC/USDT"):
    try:
        exchange = ccxt.okx({'enableRateLimit': True})
        ticker = exchange.fetch_ticker(symbol)
        return {
            "success": True,
            "exchange": "OKX",
            "price": ticker['last'],
            "change": ticker.get('percentage', 0)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
