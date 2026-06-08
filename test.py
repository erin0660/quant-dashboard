import requests
import json
from datetime import datetime, timedelta, timezone
from jinja2 import Environment, FileSystemLoader
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_crypto_price(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        return requests.get(url, headers=HEADERS, timeout=10).json()[coin_id]["usd"]
    except: return "N/A"

def get_fear_and_greed_index():
    try:
        url = "https://api.alternative.me/fng/"
        data = requests.get(url, headers=HEADERS, timeout=10).json()["data"][0]
        return {"value": int(data["value"]), "classification": data["value_classification"]}
    except: return {"value": 50, "classification": "N/A"}

def get_funding_rate(coin):
    try:
        url = f"https://www.okx.com/api/v5/public/funding-rate?instId={coin}-USDT-SWAP"
        rate = float(requests.get(url, headers=HEADERS, timeout=10).json()['data'][0]['fundingRate']) * 100
        return f"+{rate:.5f}%" if rate > 0 else f"{rate:.5f}%"
    except: return "N/A"

def get_stablecoin_mcap():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=tether,usd-coin&vs_currencies=usd&include_market_cap=true"
        data = requests.get(url, headers=HEADERS, timeout=10).json()
        return {
            "usdt": f"${data['tether']['usd_market_cap'] / 1e9:.2f} B",
            "usdc": f"${data['usd-coin']['usd_market_cap'] / 1e9:.2f} B"
        }
    except: return {"usdt": "****", "usdc": "****"}

def get_top_movers():
    try:
        url = "https://api.mexc.com/api/v3/ticker/24hr"
        data = requests.get(url, headers=HEADERS, timeout=10).json()
        usdt_pairs = [d for d in data if d['symbol'].endswith('USDT')]
        usdt_pairs.sort(key=lambda x: float(x['priceChangePercent']), reverse=True)
        return [{"symbol": item['symbol'].replace('USDT', ''), "price": f"${float(item['lastPrice']):.4f}", "change": f"+{float(item['priceChangePercent']):.2f}%"} for item in usdt_pairs[:5]]
    except: return []

def get_derivatives_data():
    try:
        tickers_res = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SWAP", headers=HEADERS, timeout=10).json()['data']
        ticker_map = {}
        
        # 🟢 新增：計算整體市場漲跌比例
        up_count = down_count = flat_count = 0
        
        for item in tickers_res:
            if item['instId'].endswith('-USDT-SWAP'):
                last_price = float(item['last'])
                open_price = float(item['open24h'])
                
                # 計算漲跌
                if last_price > open_price: up_count += 1
                elif last_price < open_price: down_count += 1
                else: flat_count += 1
                
                ticker_map[item['instId']] = {
                    'price': last_price,
                    'vol_usd': float(item['volCcy24h']) * last_price
                }

        total_contracts = up_count + down_count + flat_count
        market_breadth = {
            "up": up_count, "down": down_count, "flat": flat_count, "total": total_contracts,
            "up_pct": round((up_count / total_contracts) * 100, 1) if total_contracts else 0,
            "down_pct": round((down_count / total_contracts) * 100, 1) if total_contracts else 0,
            "flat_pct": round((flat_count / total_contracts) * 100, 1) if total_contracts else 0
        }

        oi_res = requests.get("https://www.okx.com/api/v5/public/open-interest?instType=SWAP", headers=HEADERS, timeout=10).json()['data']
        valid_pairs = []
        btc_oi = eth_oi = btc_vol = eth_vol = 0
        
        for item in oi_res:
            inst_id = item['instId']
            if inst_id not in ticker_map: continue
            
            symbol = inst_id.split('-')[0]
            price = ticker_map[inst_id]['price']
            vol_usd = ticker_map[inst_id]['vol_usd']
            oi_usd = float(item['oiCcy']) * price
            
            if symbol == 'BTC': btc_oi = oi_usd; btc_vol = vol_usd
            elif symbol == 'ETH': eth_oi = oi_usd; eth_vol = vol_usd
                
            if oi_usd > 5000000:  
                ratio = vol_usd / oi_usd if oi_usd > 0 else 0
                valid_pairs.append({"symbol": symbol, "oi": f"${oi_usd / 1e6:.1f}M", "ratio": f"{ratio:.2f}"})
        
        valid_pairs.sort(key=lambda x: float(x['ratio']), reverse=True)
        
        return {
            "btc_oi": f"${btc_oi / 1e9:.2f}B", "btc_vol": f"${btc_vol / 1e9:.2f}B", "btc_ratio": f"{btc_vol / btc_oi:.2f}" if btc_oi else "N/A",
            "eth_oi": f"${eth_oi / 1e9:.2f}B", "eth_vol": f"${eth_vol / 1e9:.2f}B", "eth_ratio": f"{eth_vol / eth_oi:.2f}" if eth_oi else "N/A",
            "top_oi_movers": valid_pairs[:5],
            "market_breadth": market_breadth
        }
    except Exception as e:
        print(f"OI 抓取失敗: {e}")
        return {
            "btc_oi": "N/A", "btc_vol": "N/A", "btc_ratio": "N/A", "eth_oi": "N/A", "eth_vol": "N/A", "eth_ratio": "N/A",
            "top_oi_movers": [{"symbol": "API 阻擋", "oi": "N/A", "ratio": "N/A"}],
            "market_breadth": {"up": 0, "down": 0, "flat": 0, "total": 0, "up_pct": 0, "down_pct": 0, "flat_pct": 0}
        }

if __name__ == "__main__":
    print("正在獲取市場數據...")
    tz_tpe = timezone(timedelta(hours=8))
    current_time = datetime.now(tz_tpe).strftime("%Y-%m-%d %H:%M:%S")
    
    btc_price = get_crypto_price("bitcoin")
    eth_price = get_crypto_price("ethereum")
    fgi_data = get_fear_and_greed_index()
    stablecoins = get_stablecoin_mcap()
    deriv_data = get_derivatives_data()

    data = {
        "update_time": current_time,
        "btc_price": f"${btc_price:,}" if isinstance(btc_price, (int, float)) else btc_price,
        "eth_price": f"${eth_price:,}" if isinstance(eth_price, (int, float)) else eth_price,
        "fgi_value": fgi_data["value"],
        "fgi_classification": fgi_data["classification"],
        "btc_funding": get_funding_rate("BTC"),
        "eth_funding": get_funding_rate("ETH"),
        "usdt_mcap": stablecoins["usdt"],
        "usdc_mcap": stablecoins["usdc"],
        "top_movers": get_top_movers(),
        
        "btc_oi": deriv_data["btc_oi"],
        "btc_vol": deriv_data["btc_vol"],
        "btc_ratio": deriv_data["btc_ratio"],
        "eth_oi": deriv_data["eth_oi"],
        "eth_vol": deriv_data["eth_vol"],
        "eth_ratio": deriv_data["eth_ratio"],
        "top_oi_movers": deriv_data["top_oi_movers"],
        
        # 🟢 傳遞真實市場廣度數據
        "mb": deriv_data["market_breadth"],
        
        # 🟡 靜態/待串接欄位
        "cb_premium": "****", "btc_options_text": "**** (待串接)", 
        "eth_options_text": "**** (待串接)", "btc_liq_text": "**** (待串接)", "eth_liq_text": "**** (待串接)"
    }

    env = Environment(loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__)) or '.'))
    template = env.get_template('template.html')
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(template.render(data))
    print("✅ 真實數據版網頁生成成功！")
