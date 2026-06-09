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

def get_core_futures_data(coin):
    # 使用 OKX API 抓取 BTC/ETH 核心數據 (穩定度高)
    try:
        url = f"https://www.okx.com/api/v5/market/ticker?instId={coin}-USDT-SWAP"
        data = requests.get(url, headers=HEADERS, timeout=10).json()['data'][0]
        
        price = float(data['last'])
        vol_usd = float(data['volCcy24h']) # 24H 成交額 (USDT)
        
        # 抓取 OI
        oi_url = f"https://www.okx.com/api/v5/public/open-interest?instId={coin}-USDT-SWAP"
        oi_data = requests.get(oi_url, headers=HEADERS, timeout=10).json()['data'][0]
        oi_coin = float(oi_data['oi']) # 張數
        
        # OKX 1張 BTC = 0.01 BTC, 1張 ETH = 0.1 ETH
        multiplier = 0.01 if coin == "BTC" else 0.1
        oi_usd = oi_coin * multiplier * price
        
        ratio = vol_usd / oi_usd if oi_usd > 0 else 0
        return f"${oi_usd/1e9:.2f}B", f"${vol_usd/1e9:.2f}B", f"{ratio:.2f}"
    except: return "****", "****", "****"

def get_top_movers():
    # MEXC 現貨強勢榜
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

def get_okx_oi_movers():
    # 使用 OKX API 抓取資金異動榜 (解決 GitHub 擋 IP 問題)
    try:
        url = "https://www.okx.com/api/v5/market/tickers?instType=SWAP"
        data = requests.get(url, headers=HEADERS, timeout=10).json()['data']
        
        results = []
        for item in data:
            if not item['instId'].endswith('-USDT-SWAP'): continue
            symbol = item['instId'].split('-')[0]
            if symbol in ['BTC', 'ETH']: continue
            
            price = float(item['last'])
            open24h = float(item['sod24h'])
            change_raw = ((price - open24h) / open24h) * 100 if open24h > 0 else 0
            vol_usd = float(item['volCcy24h'])
            
            # 為了避免抓取太慢，我們只針對成交量大於 5000 萬美金的熱門幣去抓 OI
            if vol_usd < 50000000: continue
            
            try:
                oi_url = f"https://www.okx.com/api/v5/public/open-interest?instId={item['instId']}"
                oi_data = requests.get(oi_url, headers=HEADERS, timeout=5).json()['data'][0]
                # 簡化計算：直接用合約張數 * 價格 (僅作活躍度相對比較)
                oi_val = float(oi_data['oi']) * price / 100 # 粗略換算
                
                if oi_val > 1000000: # 排除極小 OI
                    ratio = vol_usd / oi_val
                    results.append({
                        "symbol": symbol,
                        "price": f"${price:.4f}" if price < 1 else f"${price:.2f}",
                        "change": f"+{change_raw:.2f}%" if change_raw > 0 else f"{change_raw:.2f}%",
                        "change_raw": change_raw,
                        "oi_usd_val": oi_val,
                        "oi": f"${oi_val/1000000:.1f}M",
                        "ratio_val": ratio,
                        "ratio": f"{ratio:.1f}x"
                    })
            except: continue
            
        results.sort(key=lambda x: x['ratio_val'], reverse=True)
        return results[:10]
    except: return []

if __name__ == "__main__":
    tz_tpe = timezone(timedelta(hours=8))
    
    mcap_val, mcap_change = get_global_mcap()
    btc_oi, btc_vol, btc_ratio = get_core_futures_data("BTC")
    eth_oi, eth_vol, eth_ratio = get_core_futures_data("ETH")

    data = {
        "update_time": datetime.now(tz_tpe).strftime("%Y-%m-%d %H:%M:%S"),
        "btc_price": f"${get_crypto_price('bitcoin'):,}",
        "eth_price": f"${get_crypto_price('ethereum'):,}",
        "fgi_value": 50, "fgi_classification": "中性",
        "btc_funding": get_funding_rate("BTC"), "eth_funding": get_funding_rate("ETH"),
        
        "total_mcap": mcap_val, "total_mcap_change": mcap_change,
        "btc_oi": btc_oi, "btc_vol": btc_vol, "btc_ratio": btc_ratio,
        "eth_oi": eth_oi, "eth_vol": eth_vol, "eth_ratio": eth_ratio,
        
        "usdt_mcap": "****", "usdt_change": "****",
        "usdc_mcap": "****", "usdc_change": "****",
        "mb": {"up": "****", "down": "****", "flat": "****", "total": "****", "up_pct": 0, "down_pct": 0, "flat_pct": 0},
        "deribit_btc": {"pcr": "****", "sentiment": "****", "total_oi": "****", "iv": "****", "max_pain": "****", "next_expiry": "****"},
        "deribit_eth": {"pcr": "****", "sentiment": "****", "total_oi": "****", "iv": "****", "max_pain": "****", "next_expiry": "****"},
        
        "top_movers": get_top_movers(),           
        "top_oi_movers": get_okx_oi_movers(), 
    }
    
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('template.html')
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(template.render(data))
