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
        response = requests.get(url, headers=HEADERS, timeout=10)
        return response.json()[coin_id]["usd"]
    except:
        return "N/A"

def get_fear_and_greed_index():
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url, headers=HEADERS, timeout=10)
        data = response.json()["data"][0]
        return {"value": data["value"], "classification": data["value_classification"]}
    except:
        return {"value": "N/A", "classification": "N/A"}

def get_funding_rate(coin):
    try:
        url = f"https://www.okx.com/api/v5/public/funding-rate?instId={coin}-USDT-SWAP"
        response = requests.get(url, headers=HEADERS, timeout=10)
        rate = float(response.json()['data'][0]['fundingRate']) * 100
        return f"+{rate:.5f}%" if rate > 0 else f"{rate:.5f}%"
    except:
        return "N/A"

# 🟢 新增：真實獲取穩定幣市值 (CoinGecko)
def get_stablecoin_mcap():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=tether,usd-coin&vs_currencies=usd&include_market_cap=true"
        response = requests.get(url, headers=HEADERS, timeout=10)
        data = response.json()
        return {
            "usdt": f"${data['tether']['usd_market_cap'] / 1e9:.2f} B",
            "usdc": f"${data['usd-coin']['usd_market_cap'] / 1e9:.2f} B"
        }
    except:
        return {"usdt": "****", "usdc": "****"}

# 🟢 加回：真實獲取 24H 強勢幣種 (MEXC)
def get_top_movers():
    try:
        url = "https://api.mexc.com/api/v3/ticker/24hr"
        response = requests.get(url, headers=HEADERS, timeout=10)
        data = response.json()
        usdt_pairs = [d for d in data if d['symbol'].endswith('USDT')]
        usdt_pairs.sort(key=lambda x: float(x['priceChangePercent']), reverse=True)
        top_5 = []
        for item in usdt_pairs[:5]:
            top_5.append({
                "symbol": item['symbol'].replace('USDT', ''),
                "price": f"${float(item['lastPrice']):.4f}",
                "change": f"+{float(item['priceChangePercent']):.2f}%"
            })
        return top_5
    except:
        return []

if __name__ == "__main__":
    print("正在獲取市場數據...")
    tz_tpe = timezone(timedelta(hours=8))
    current_time = datetime.now(tz_tpe).strftime("%Y-%m-%d %H:%M:%S")
    
    btc_price = get_crypto_price("bitcoin")
    eth_price = get_crypto_price("ethereum")
    fgi_data = get_fear_and_greed_index()
    stablecoins = get_stablecoin_mcap()

    # 組合數據：真實數據 + 星號遮蔽
    data = {
        "update_time": current_time,
        
        # 🟢 真實數據區
        "btc_price": f"${btc_price:,}" if isinstance(btc_price, (int, float)) else btc_price,
        "eth_price": f"${eth_price:,}" if isinstance(eth_price, (int, float)) else eth_price,
        "fgi_value": fgi_data["value"],
        "fgi_classification": fgi_data["classification"],
        "btc_funding": get_funding_rate("BTC"),
        "eth_funding": get_funding_rate("ETH"),
        "usdt_mcap": stablecoins["usdt"],
        "usdc_mcap": stablecoins["usdc"],
        "top_movers": get_top_movers(),
        
        # 🟡 尚未串接 API 的欄位，全部改為 ****
        "dxy_index": "****",
        "gold_price": "****",
        "tga_balance": "****",
        "usdt_flow": "****",
        "usdc_vol_ratio": "****",
        "cb_premium": "****",
        "btc_exchange_flow": "****",
        "btc_lth": "****",
        "eth_exchange_flow": "****",
        "eth_top100": "****",
        "btc_oi": "****",
        "btc_oi_change": "****",
        "btc_vol_oi_ratio": "****",
        "eth_oi": "****",
        "eth_oi_change": "****",
        "btc_options_text": "**** (待串接)",
        "eth_options_text": "**** (待串接)",
        "btc_liq_text": "**** (待串接)",
        "eth_liq_text": "**** (待串接)"
    }

    env = Environment(loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__)) or '.'))
    template = env.get_template('template.html')
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(template.render(data))
    print("✅ 真實數據版網頁生成成功！")
