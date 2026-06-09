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
    # 串接 CoinGecko 全球總市值
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

def get_binance_futures_core(symbol):
    # 串接幣安合約 BTC/ETH 核心數據
    try:
        ticker_url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}USDT"
        ticker = requests.get(ticker_url, timeout=5).json()
        vol_usd = float(ticker['quoteVolume'])
        price = float(ticker['lastPrice'])
        
        oi_url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}USDT"
        oi_data = requests.get(oi_url, timeout=5).json()
        oi_usd = float(oi_data['openInterest']) * price
        
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

def get_binance_oi_movers():
    # 幣安合約資金異動榜 (解決 Bybit 擋 IP 問題)
    try:
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        data = requests.get(url, headers=HEADERS, timeout=10).json()
        
        # 篩選 USDT 合約並依照成交量排序，先抓前 20 大熱門幣種
        usdt_pairs = [d for d in data if d['symbol'].endswith('USDT')]
        usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        top_20 = usdt_pairs[:20]
        
        results = []
        for item in top_20:
            symbol = item['symbol']
            if symbol in ['BTCUSDT', 'ETHUSDT']: continue # 排除大哥二哥，只看山寨
            
            price = float(item['lastPrice'])
            change_raw = float(item['priceChangePercent'])
            vol_usd = float(item['quoteVolume'])
            
            # 針對這幾個熱門幣，單獨抓取 OI
            oi_url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
            oi_data = requests.get(oi_url, headers=HEADERS, timeout=5).json()
            oi_usd = float(oi_data.get('openInterest', 0)) * price
            
            if oi_usd > 0:
                ratio = vol_usd / oi_usd
                results.append({
                    "symbol": symbol.replace('USDT', ''),
                    "price": f"${price:.4f}" if price < 1 else f"${price:.2f}",
                    "change": f"+{change_raw:.2f}%" if change_raw > 0 else f"{change_raw:.2f}%",
                    "change_raw": change_raw,
                    "oi_usd_val": oi_usd,
                    "oi": f"${oi_usd/1000000:.1f}M",
                    "ratio_val": ratio,
                    "ratio": f"{ratio:.1f}x"
                })
        
        # 依照活躍度 (Vol/OI) 重新排序，抓取前 10 名
        results.sort(key=lambda x: x['ratio_val'], reverse=True)
        return results[:10]
    except: return []

if __name__ == "__main__":
    tz_tpe = timezone(timedelta(hours=8))
    
    # 獲取大盤與核心數據
    mcap_val, mcap_change = get_global_mcap()
    btc_oi, btc_vol, btc_ratio = get_binance_futures_core("BTC")
    eth_oi, eth_vol, eth_ratio = get_binance_futures_core("ETH")

    data = {
        "update_time": datetime.now(tz_tpe).strftime("%Y-%m-%d %H:%M:%S"),
        "btc_price": f"${get_crypto_price('bitcoin'):,}",
        "eth_price": f"${get_crypto_price('ethereum'):,}",
        "fgi_value": 50, "fgi_classification": "中性",
        "btc_funding": get_funding_rate("BTC"), "eth_funding": get_funding_rate("ETH"),
        
        # 剛接好的真實數據
        "total_mcap": mcap_val, "total_mcap_change": mcap_change,
        "btc_oi": btc_oi, "btc_vol": btc_vol, "btc_ratio": btc_ratio,
        "eth_oi": eth_oi, "eth_vol": eth_vol, "eth_ratio": eth_ratio,
        
        # 尚未接好的維持 ****
        "usdt_mcap": "****", "usdt_change": "****",
        "usdc_mcap": "****", "usdc_change": "****",
        "mb": {"up": "****", "down": "****", "flat": "****", "total": "****", "up_pct": 0, "down_pct": 0, "flat_pct": 0},
        "deribit_btc": {"pcr": "****", "sentiment": "****", "total_oi": "****", "iv": "****", "max_pain": "****", "next_expiry": "****"},
        "deribit_eth": {"pcr": "****", "sentiment": "****", "total_oi": "****", "iv": "****", "max_pain": "****", "next_expiry": "****"},
        
        # 兩大排行榜 (真實數據)
        "top_movers": get_top_movers(),           
        "top_oi_movers": get_binance_oi_movers(), 
    }
    
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('template.html')
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(template.render(data))
