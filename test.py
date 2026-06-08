import requests
import json
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import os

def get_crypto_price(coin_id):
    """獲取加密貨幣價格 (CoinGecko)"""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        data = response.json()
        return data[coin_id]["usd"]
    except Exception as e:
        print(f"獲取 {coin_id} 價格失敗: {e}")
        return "N/A"

def get_fear_and_greed_index():
    """獲取恐懼與貪婪指數"""
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
    """從幣安合約 API 獲取即時資金費率"""
    try:
        url = "https://fapi.binance.com/fapi/v1/premiumIndex"
        params = {"symbol": symbol}
        response = requests.get(url, timeout=10, params=params)
        data = response.json()
        rate = float(data['lastFundingRate']) * 100
        return f"+{rate:.4f}%" if rate > 0 else f"{rate:.4f}%"
    except Exception as e:
        print(f"獲取 {symbol} 資金費率失敗: {e}")
        return "N/A"

def get_top_movers():
    """從幣安公開 API 獲取 24 小時漲幅前 5 名的合約幣種"""
    try:
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # 篩選 USDT 交易對
        usdt_pairs = [d for d in data if d['symbol'].endswith('USDT')]
        # 依照漲跌幅排序
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
    
    # 1. 抓取真實數據
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    btc_price = get_crypto_price("bitcoin")
    eth_price = get_crypto_price("ethereum")
    fgi_data = get_fear_and_greed_index()
    btc_funding = get_funding_rate("BTCUSDT")
    eth_funding = get_funding_rate("ETHUSDT")
    top_movers = get_top_movers()

    # 2. 準備傳入模板的數據字典 (包含真實數據與模擬佔位數據)
    data = {
        "update_time": current_time,
        "btc_price": f"${btc_price:,}" if isinstance(btc_price, (int, float)) else btc_price,
        "eth_price": f"${eth_price:,}" if isinstance(eth_price, (int, float)) else eth_price,
        "fgi_value": fgi_data["value"],
        "fgi_classification": fgi_data["classification"],
        "btc_funding": btc_funding,
        "eth_funding": eth_funding,
        "top_movers": top_movers,
        
        # 以下為模擬數據 (Phase 2 後續替換)
        "dxy_index": "104.25",
        "gold_price": "$2,350.10",
        "usdt_mcap": "$110.5B",
        "usdc_mcap": "$32.1B"
    }

    # 3. 渲染 HTML 模板
    print("正在生成網頁...")
    # 使用相對路徑讀取 template.html
    env = Environment(loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__)) or '.'))
    template = env.get_template('template.html')
    output_html = template.render(data)

    # 4. 輸出結果到 index.html
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(output_html)
        
    print("✅ 網頁生成成功！請查看 index.html")


if __name__ == "__main__":
    generate_dashboard()
