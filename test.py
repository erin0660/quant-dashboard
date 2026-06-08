import requests
import json
from datetime import datetime, timedelta, timezone
from jinja2 import Environment, FileSystemLoader
import os

def get_crypto_price(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        data = response.json()
        return data[coin_id]["usd"]
    except Exception as e:
        print(f"獲取 {coin_id} 價格失敗: {e}")
        return "N/A"

def get_fear_and_greed_index():
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url, timeout=10)
        data = response.json()
        fgi_value = data["data"][0]["value"]
        fgi_class = data["data"][0]["value_classification"]
        return {"value": fgi_value, "classification": fgi_class}
    except Exception as e:
        print(f"獲取恐懼與貪婪指數失敗: {e}")
        return {"value": "N/A", "classification": "N/A"}

def get_funding_rate(symbol):
    try:
        # 改用 Bybit API 獲取資金費率，完美避開幣安阻擋美國 IP 的問題
        url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}"
        response = requests.get(url, timeout=10)
        data = response.json()
        rate = float(data['result']['list'][0]['fundingRate']) * 100
        return f"+{rate:.4f}%" if rate > 0 else f"{rate:.4f}%"
    except Exception as e:
        print(f"獲取 {symbol} 資金費率失敗: {e}")
        return "N/A"

def get_top_movers():
    try:
        # 改用幣安「現貨 (Spot)」API，現貨 API 不會阻擋美國 IP
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url, timeout=10)
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
    except Exception as e:
        print(f"獲取排名失敗: {e}")
        return []

if __name__ == "__main__":
    print("正在獲取市場數據...")
    
    # 設定台灣時間 (UTC+8)
    tz_tpe = timezone(timedelta(hours=8))
    current_time = datetime.now(tz_tpe).strftime("%Y-%m-%d %H:%M:%S")
    
    btc_price = get_crypto_price("bitcoin")
    eth_price = get_crypto_price("ethereum")
    fgi_data = get_fear_and_greed_index()
    btc_funding = get_funding_rate("BTCUSDT")
    eth_funding = get_funding_rate("ETHUSDT")
    top_movers = get_top_movers()

    data = {
        "update_time": current_time,
        "btc_price": f"${btc_price:,}" if isinstance(btc_price, (int, float)) else btc_price,
        "eth_price": f"${eth_price:,}" if isinstance(eth_price, (int, float)) else eth_price,
        "fgi_value": fgi_data["value"],
        "fgi_classification": fgi_data["classification"],
        "btc_funding": btc_funding,
        "eth_funding": eth_funding,
        "top_movers": top_movers,
        "dxy_index": "104.25",
        "gold_price": "$2,350.10",
        "usdt_mcap": "$110.5B",
        "usdc_mcap": "$32.1B"
    }

    print("正在生成網頁...")
    env = Environment(loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__)) or '.'))
    template = env.get_template('template.html')
    output_html = template.render(data)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(output_html)
        
    print("✅ 網頁生成成功！請查看 index.html")
