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
        return {"value": data["value"], "classification": data["value_classification"]}
    except: return {"value": "N/A", "classification": "N/A"}

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

# 🟢 新增：真實獲取衍生品 OI 與資金異動排名 (Bybit API)
def get_derivatives_data():
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=linear"
        data = requests.get(url, headers=HEADERS, timeout=10).json()['result']['list']
        
        # 1. 提取 BTC 與 ETH 真實數據
        btc = next(item for item in data if item['symbol'] == 'BTCUSDT')
        eth = next(item for item in data if item['symbol'] == 'ETHUSDT')
        
        btc_oi = float(btc['openInterest']) * float(btc['lastPrice'])
        btc_vol = float(btc['turnover24h'])
        eth_oi = float(eth['openInterest']) * float(eth['lastPrice'])
        eth_vol = float(eth['turnover24h'])
        
        # 2. 計算全市場資金異動 (過濾掉 OI 小於 500萬美金的冷門幣)
        valid_pairs = []
        for item in data:
            if item['symbol'].endswith('USDT'):
                oi_usd = float(item['openInterest']) * float(item['lastPrice'])
                vol_usd = float(item['turnover24h'])
                if oi_usd > 5000000:  
                    ratio = vol_usd / oi_usd
                    valid_pairs.append({
                        "symbol": item['symbol'].replace('USDT', ''),
                        "oi": f"${oi_usd / 1e6:.1f}M",
                        "ratio": f"{ratio:.2f}"
                    })
        
        # 依照活躍度 (Vol/OI) 降冪排序，取前 5 名
        valid_pairs.sort(key=lambda x: float(x['ratio']), reverse=True)
        
        return {
            "btc_oi": f"${btc_oi / 1e9:.2f}B",
            "btc_vol": f"${btc_vol / 1e9:.2f}B",
            "btc_ratio": f"{btc_vol / btc_oi:.2f}",
            "eth_oi": f"${eth_oi / 1e9:.2f}B",
            "eth_vol": f"${eth_vol / 1e9:.2f}B",
            "eth_ratio": f"{eth_vol / eth_oi:.2f}",
            "top_oi_movers": valid_pairs[:5]
        }
    except Exception as e:
        print(f"OI 抓取失敗: {e}")
        return None

if __name__ == "__main__":
    print("正在獲取市場數據...")
    tz_tpe = timezone(timedelta(hours=8))
    current_time = datetime.now(tz_tpe).strftime("%Y-%m-%d %H:%M:%S")
    
    btc_price = get_crypto_price("bitcoin")
    eth_price = get_crypto_price("ethereum")
    fgi_data = get_fear_and_greed_index()
    stablecoins = get_stablecoin_mcap()
    deriv_data = get_derivatives_data() or {}

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
        
        # 🟢 真實衍生品數據
        "btc_oi": deriv_data.get("btc_oi", "N/A"),
        "btc_vol": deriv_data.get("btc_vol", "N/A"),
        "btc_ratio": deriv_data.get("btc_ratio", "N/A"),
        "eth_oi": deriv_data.get("eth_oi", "N/A"),
        "eth_vol": deriv_data.get("eth_vol", "N/A"),
        "eth_ratio": deriv_data.get("eth_ratio", "N/A"),
        "top_oi_movers": deriv_data.get("top_oi_movers", []),
        
        # 🟡 尚未串接的靜態欄位
        "dxy_index": "****", "gold_price": "****", "tga_balance": "****",
        "usdt_flow": "****", "usdc_vol_ratio": "****", "cb_premium": "****",
        "btc_exchange_flow": "****", "btc_lth": "****", "eth_exchange_flow": "****",
        "eth_top100": "****", "btc_options_text": "**** (待串接)", 
        "eth_options_text": "**** (待串接)", "btc_liq_text": "**** (待串接)", 
        "eth_liq_text": "**** (待串接)"
    }

    env = Environment(loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__)) or '.'))
    template = env.get_template('template.html')
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(template.render(data))
    print("✅ 真實數據版網頁生成成功！")
