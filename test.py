import requests
from datetime import datetime, timedelta, timezone
from jinja2 import Environment, FileSystemLoader
import os

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def get_crypto_price(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        return requests.get(url, headers=HEADERS, timeout=10).json()[coin_id]["usd"]
    except: return "N/A"

def get_funding_rate(coin):
    try:
        url = f"https://www.okx.com/api/v5/public/funding-rate?instId={coin}-USDT-SWAP"
        rate = float(requests.get(url, headers=HEADERS, timeout=10).json()['data'][0]['fundingRate']) * 100
        return f"+{rate:.5f}%" if rate > 0 else f"{rate:.5f}%"
    except: return "N/A"

def get_top_movers():
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
                "oi": "$--M",   # 現貨榜單暫無合約 OI，以佔位符顯示保持版面一致
                "ratio": "--"
            })
        return results
    except: return []

if __name__ == "__main__":
    tz_tpe = timezone(timedelta(hours=8))
    
    # 模擬 10 筆資金異動數據
    mock_oi_movers = [
        {"symbol": "ALLO", "price": "$0.4158", "change": "+26.90%", "change_raw": 26.9, "oi": "$8.3M", "ratio": "60.02"},
        {"symbol": "PIPPIN", "price": "$0.0255", "change": "+42.98%", "change_raw": 42.98, "oi": "$6.1M", "ratio": "33.58"},
        {"symbol": "BSB", "price": "$0.3021", "change": "-10.06%", "change_raw": -10.06, "oi": "$5.8M", "ratio": "27.05"},
        {"symbol": "BEAT", "price": "$4.36", "change": "+28.68%", "change_raw": 28.68, "oi": "$41.5M", "ratio": "16.72"},
        {"symbol": "WLD", "price": "$0.4959", "change": "+6.12%", "change_raw": 6.12, "oi": "$38.8M", "ratio": "12.84"},
        {"symbol": "SOL", "price": "$145.20", "change": "+3.15%", "change_raw": 3.15, "oi": "$2.1B", "ratio": "8.50"},
        {"symbol": "PEPE", "price": "$0.00001", "change": "+15.2%", "change_raw": 15.2, "oi": "$150M", "ratio": "7.20"},
        {"symbol": "ORDI", "price": "$45.30", "change": "-5.40%", "change_raw": -5.4, "oi": "$85M", "ratio": "6.80"},
        {"symbol": "TIA", "price": "$12.10", "change": "+8.90%", "change_raw": 8.9, "oi": "$120M", "ratio": "5.90"},
        {"symbol": "FET", "price": "$2.30", "change": "+11.2%", "change_raw": 11.2, "oi": "$95M", "ratio": "5.10"}
    ]

    data = {
        "update_time": datetime.now(tz_tpe).strftime("%Y-%m-%d %H:%M:%S"),
        "btc_price": f"${get_crypto_price('bitcoin'):,}",
        "eth_price": f"${get_crypto_price('ethereum'):,}",
        "fgi_value": 50, "fgi_classification": "中性",
        "btc_funding": get_funding_rate("BTC"), "eth_funding": get_funding_rate("ETH"),
        
        # 新增市值與穩定幣漲跌幅 (此處先以靜態模擬，未來可串接 API)
        "total_mcap": "$2.45 T", "total_mcap_change": "+1.20%",
        "usdt_mcap": "$186.89 B", "usdt_change": "+0.15%",
        "usdc_mcap": "$75.97 B", "usdc_change": "-0.05%",
        
        "top_movers": get_top_movers(),
        "top_oi_movers": mock_oi_movers,
        "btc_oi": "$1.79B", "btc_vol": "$7.35B", "btc_ratio": "4.12",
        "eth_oi": "$1.17B", "eth_vol": "$7.99B", "eth_ratio": "6.80",
        "mb": {"up": 179, "down": 169, "flat": 1, "total": 349, "up_pct": 51, "down_pct": 48, "flat_pct": 1},
        
        "deribit_btc": {"pcr": "0.65", "sentiment": "偏多", "total_oi": "430,021 顆", "iv": "48.5%", "max_pain": "$62,000", "next_expiry": "本週五 (名目 $1.2B)"},
        "deribit_eth": {"pcr": "0.53", "sentiment": "偏多", "total_oi": "2,126,431 顆", "iv": "52.1%", "max_pain": "$1,600", "next_expiry": "本週五 (名目 $850M)"}
    }
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('template.html')
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(template.render(data))
