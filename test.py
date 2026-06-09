import requests
from datetime import datetime, timedelta, timezone
from jinja2 import Environment, FileSystemLoader
import os

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def get_crypto_price(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        return requests.get(url, headers=HEADERS, timeout=10).json()[coin_id]["usd"]
    except: return "****"

def get_funding_rate(coin):
    try:
        url = f"https://www.okx.com/api/v5/public/funding-rate?instId={coin}-USDT-SWAP"
        rate = float(requests.get(url, headers=HEADERS, timeout=10).json()['data'][0]['fundingRate']) * 100
        return f"+{rate:.5f}%" if rate > 0 else f"{rate:.5f}%"
    except: return "****"

def get_top_movers():
    # MEXC 現貨強勢榜 (真實數據)
    try:
        url = "https://api.mexc.com/api/v3/ticker/24hr"
        data = requests.get(url, headers=HEADERS, timeout=10).json()
        usdt_pairs = [d for d in data if d['symbol'].endswith('USDT')]
        usdt_pairs.sort(key=lambda x: float(x.get('priceChangePercent', 0)), reverse=True)
        results = []
        for item in usdt_pairs[:10]:
            change_val = float(item.get('priceChangePercent', 0))
            results.append({
                "symbol": item['symbol'].replace('USDT', ''),
                "price": f"${float(item['lastPrice']):.4f}",
                "change": f"+{change_val:.2f}%" if change_val > 0 else f"{change_val:.2f}%",
                "change_raw": change_val,
                "oi": "****",   # 現貨無 OI
                "ratio": "****" # 現貨無活躍度
            })
        return results
    except: return []

def get_bybit_oi_movers():
    # Bybit 合約資金異動榜 (真實數據)
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=linear"
        data = requests.get(url, headers=HEADERS, timeout=10).json()
        if data.get("retCode") != 0: return []
        
        results = []
        for item in data["result"]["list"]:
            if not item["symbol"].endswith("USDT"): continue
            
            symbol = item["symbol"].replace("USDT", "")
            price = float(item["lastPrice"])
            change_raw = float(item["price24hPcnt"]) * 100  # Bybit 漲跌幅是小數，需乘 100
            turnover = float(item["turnover24h"])           # 24H 成交額 (USDT)
            oi_coin = float(item["openInterest"])           # 未平倉量 (幣本位)
            oi_usd = oi_coin * price                        # 換算為 USD 價值
            
            # 過濾掉 OI 小於 100 萬美金的冷門幣，避免活躍度失真
            if oi_usd < 1000000: continue
            
            ratio = turnover / oi_usd if oi_usd > 0 else 0
            
            results.append({
                "symbol": symbol,
                "price": f"${price:.4f}" if price < 1 else f"${price:.2f}",
                "change": f"+{change_raw:.2f}%" if change_raw > 0 else f"{change_raw:.2f}%",
                "change_raw": change_raw,
                "oi_usd_val": oi_usd,
                "oi": f"${oi_usd/1000000:.1f}M",
                "ratio_val": ratio,
                "ratio": f"{ratio:.1f}"
            })
        
        # 依照活躍度 (Vol/OI) 降冪排序，抓取前 10 名
        results.sort(key=lambda x: x["ratio_val"], reverse=True)
        return results[:10]
    except: return []

if __name__ == "__main__":
    tz_tpe = timezone(timedelta(hours=8))
    
    data = {
        "update_time": datetime.now(tz_tpe).strftime("%Y-%m-%d %H:%M:%S"),
        "btc_price": f"${get_crypto_price('bitcoin'):,}",
        "eth_price": f"${get_crypto_price('ethereum'):,}",
        "fgi_value": 50, "fgi_classification": "中性",
        "btc_funding": get_funding_rate("BTC"), "eth_funding": get_funding_rate("ETH"),
        
        # 未串接 API 的欄位嚴格使用 ****
        "total_mcap": "****", "total_mcap_change": "****",
        "usdt_mcap": "****", "usdt_change": "****",
        "usdc_mcap": "****", "usdc_change": "****",
        
        "top_movers": get_top_movers(),           # MEXC 真實現貨數據
        "top_oi_movers": get_bybit_oi_movers(),   # Bybit 真實合約數據
        
        "btc_oi": "****", "btc_vol": "****", "btc_ratio": "****",
        "eth_oi": "****", "eth_vol": "****", "eth_ratio": "****",
        "mb": {"up": "****", "down": "****", "flat": "****", "total": "****", "up_pct": 0, "down_pct": 0, "flat_pct": 0},
        
        "deribit_btc": {"pcr": "****", "sentiment": "****", "total_oi": "****", "iv": "****", "max_pain": "****", "next_expiry": "****"},
        "deribit_eth": {"pcr": "****", "sentiment": "****", "total_oi": "****", "iv": "****", "max_pain": "****", "next_expiry": "****"}
    }
    
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('template.html')
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(template.render(data))
