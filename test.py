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

def get_global_mcap():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        data = requests.get(url, headers=HEADERS, timeout=10).json()['data']
        mcap = data['total_market_cap']['usd']
        change = data['market_cap_change_percentage_24h_usd']
        return f"${mcap/1e12:.2f} T", f"+{change:.2f}%" if change > 0 else f"{change:.2f}%"
    except: return "****", "****"

def get_funding_rate(coin):
    try:
        url = f"https://www.okx.com/api/v5/public/funding-rate?instId={coin}-USDT-SWAP"
        rate = float(requests.get(url, headers=HEADERS, timeout=10).json()['data'][0]['fundingRate']) * 100
        return f"+{rate:.5f}%" if rate > 0 else f"{rate:.5f}%"
    except: return "****"

def get_hyperliquid_data():
    # 使用 Hyperliquid DEX API (無 IP 限制，數據極度穩定)
    try:
        url = "https://api.hyperliquid.xyz/info"
        headers = {"Content-Type": "application/json"}
        payload = {"type": "metaAndAssetCtxs"}
        res = requests.post(url, headers=headers, json=payload, timeout=10).json()
        
        universe = res[0]["universe"]
        asset_ctxs = res[1]
        
        btc_data = {"oi": "****", "vol": "****", "ratio": "****"}
        eth_data = {"oi": "****", "vol": "****", "ratio": "****"}
        oi_movers = []
        
        for i, asset in enumerate(universe):
            symbol = asset["name"]
            ctx = asset_ctxs[i]
            
            price = float(ctx["markPx"])
            prev_price = float(ctx["prevDayPx"])
            change_raw = ((price - prev_price) / prev_price) * 100 if prev_price > 0 else 0
            
            vol_usd = float(ctx["dayNtlVlm"])
            oi_coin = float(ctx["openInterest"])
            oi_usd = oi_coin * price
            
            ratio = vol_usd / oi_usd if oi_usd > 0 else 0
            
            if symbol == "BTC":
                btc_data = {"oi": f"${oi_usd/1e9:.2f}B", "vol": f"${vol_usd/1e9:.2f}B", "ratio": f"{ratio:.2f}"}
            elif symbol == "ETH":
                eth_data = {"oi": f"${oi_usd/1e9:.2f}B", "vol": f"${vol_usd/1e9:.2f}B", "ratio": f"{ratio:.2f}"}
            else:
                # 過濾掉 24H 成交量小於 1000 萬美金的冷門幣
                if vol_usd > 10000000 and oi_usd > 1000000:
                    oi_movers.append({
                        "symbol": symbol,
                        "price": f"${price:.4f}" if price < 1 else f"${price:.2f}",
                        "change": f"+{change_raw:.2f}%" if change_raw > 0 else f"{change_raw:.2f}%",
                        "change_raw": change_raw,
                        "oi": f"${oi_usd/1000000:.1f}M",
                        "ratio_val": ratio,
                        "ratio": f"{ratio:.1f}x"
                    })
        
        # 依照活躍度排序，取前 10 名
        oi_movers.sort(key=lambda x: x["ratio_val"], reverse=True)
        return btc_data, eth_data, oi_movers[:10]
    except Exception as e:
        print(f"Hyperliquid Error: {e}")
        return {"oi": "****", "vol": "****", "ratio": "****"}, {"oi": "****", "vol": "****", "ratio": "****"}, []

def get_top_movers():
    # MEXC 現貨強勢榜 (已確認運作正常)
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
                "oi": "****", "ratio": "****"
            })
        return results
    except: return []

if __name__ == "__main__":
    tz_tpe = timezone(timedelta(hours=8))
    
    mcap_val, mcap_change = get_global_mcap()
    btc_data, eth_data, oi_movers = get_hyperliquid_data()

    data = {
        "update_time": datetime.now(tz_tpe).strftime("%Y-%m-%d %H:%M:%S"),
        "btc_price": f"${get_crypto_price('bitcoin'):,}",
        "eth_price": f"${get_crypto_price('ethereum'):,}",
        "fgi_value": 50, "fgi_classification": "中性",
        "btc_funding": get_funding_rate("BTC"), "eth_funding": get_funding_rate("ETH"),
        
        "total_mcap": mcap_val, "total_mcap_change": mcap_change,
        "btc_oi": btc_data["oi"], "btc_vol": btc_data["vol"], "btc_ratio": btc_data["ratio"],
        "eth_oi": eth_data["oi"], "eth_vol": eth_data["vol"], "eth_ratio": eth_data["ratio"],
        
        "usdt_mcap": "****", "usdt_change": "****",
        "usdc_mcap": "****", "usdc_change": "****",
        "mb": {"up": "****", "down": "****", "flat": "****", "total": "****", "up_pct": 0, "down_pct": 0, "flat_pct": 0},
        "deribit_btc": {"pcr": "****", "sentiment": "****", "total_oi": "****", "iv": "****", "max_pain": "****", "next_expiry": "****"},
        "deribit_eth": {"pcr": "****", "sentiment": "****", "total_oi": "****", "iv": "****", "max_pain": "****", "next_expiry": "****"},
        
        "top_movers": get_top_movers(),           
        "top_oi_movers": oi_movers, 
    }
    
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('template.html')
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(template.render(data))
