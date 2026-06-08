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

if __name__ == "__main__":
    print("正在獲取市場數據...")
    tz_tpe = timezone(timedelta(hours=8))
    current_time = datetime.now(tz_tpe).strftime("%Y-%m-%d %H:%M:%S")
    
    btc_price = get_crypto_price("bitcoin")
    eth_price = get_crypto_price("ethereum")
    fgi_data = get_fear_and_greed_index()

    # 組合 Pro 版數據 (真實 API + 模擬進階數據)
    data = {
        "update_time": current_time,
        # 真實數據
        "btc_price": f"${btc_price:,}" if isinstance(btc_price, (int, float)) else btc_price,
        "eth_price": f"${eth_price:,}" if isinstance(eth_price, (int, float)) else eth_price,
        "fgi_value": fgi_data["value"],
        "fgi_classification": fgi_data["classification"],
        "btc_funding": get_funding_rate("BTC"),
        "eth_funding": get_funding_rate("ETH"),
        
        # 總經與穩定幣 (模擬)
        "dxy_index": "100.11",
        "gold_price": "4,359.1 (-0.14%)",
        "tga_balance": "844,521 M (-1,201)",
        "usdt_mcap": "187.03 B",
        "usdt_flow": "-146.88 M (24h)",
        "usdc_mcap": "75.58 B",
        "usdc_vol_ratio": "0.1464",
        
        # 核心資產進階數據 (模擬)
        "cb_premium": "-0.047%",
        "btc_exchange_flow": "-4,403.17",
        "btc_lth": "16.35 M",
        "eth_exchange_flow": "-269.95 K",
        "eth_top100": "89.54%",
        
        # ETH 節點 (模擬)
        "eth_entry_queue": "3,024,096 ETH",
        "eth_wait_time": "52天 12小時",
        "eth_exit_queue": "23,246 ETH",
        
        # 衍生品 OI (模擬)
        "btc_oi": "711.36K ($44.97B)",
        "btc_oi_change": "+1.20%",
        "btc_vol_oi_ratio": "0.57",
        "eth_oi": "14.44M ($24.35B)",
        "eth_oi_change": "+4.19%",
        
        # 選擇權與清算地圖 (模擬文本)
        "btc_options_text": "260626 到期日名義金額現峰值 ($9.00B)，最大痛點達 $75.0K。",
        "eth_options_text": "260925 最大痛點折線現峰值 (接近 $2.4K)。",
        "btc_liq_text": "現價 $63,098，下方 61,040 - 63,252 區間有顯著多單清算密集區。",
        "eth_liq_text": "現價 $1,678，上方累積極大空單清算強度，峰值突破 10.00B。"
    }

    env = Environment(loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__)) or '.'))
    template = env.get_template('template.html')
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(template.render(data))
    print("✅ Pro 版網頁生成成功！")
