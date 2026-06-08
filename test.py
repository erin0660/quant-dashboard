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
        usdt_pairs.sort(key=lambda x: float(x.get('priceChangePercent', 0)), reverse=True)
        return [{"symbol": item['symbol'].replace('USDT', ''), "price": f"${float(item['lastPrice']):.4f}", "change": f"+{float(item['priceChangePercent']):.2f}%"} for item in usdt_pairs[:5]]
    except: return []

def get_options_data(currency):
    try:
        url = f"https://deribit.com/api/v2/public/get_book_summary_by_currency?currency={currency}&kind=option"
        data = requests.get(url, headers=HEADERS, timeout=10).json().get('result', [])
        call_oi = sum(item.get('open_interest', 0) for item in data if item.get('instrument_name', '').endswith('-C'))
        put_oi = sum(item.get('open_interest', 0) for item in data if item.get('instrument_name', '').endswith('-P'))
        pcr = put_oi / call_oi if call_oi > 0 else 0
        sentiment = "偏空 🐻" if pcr > 1 else ("偏多 🐂" if pcr < 0.7 else "中性 ⚖️")
        return f"PCR: {pcr:.2f} ({sentiment})<br>總持倉: {call_oi + put_oi:,.0f} 顆"
    except: return "**** (API 異常)"

def get_derivatives_data():
    fallback_data = {"btc_oi": "N/A", "btc_vol": "N/A", "btc_ratio": "N/A", "eth_oi": "N/A", "eth_vol": "N/A", "eth_ratio": "N/A", "top_oi_movers": [], "market_breadth": {"up": 0, "down": 0, "flat": 0, "total": 0, "up_pct": 0, "down_pct": 0, "flat_pct": 0}}
    try:
        tickers_res = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SWAP", headers=HEADERS, timeout=10).json().get('data', [])
        ticker_map = {}
        up_count = down_count = flat_count = 0
        
        for item in tickers_res:
            if item.get('instId', '').endswith('-USDT-SWAP'):
                last_price = float(item.get('last', 0))
                open_price = float(item.get('open24h', 0))
                change_pct = ((last_price - open_price) / open_price * 100) if open_price > 0 else 0
                
                if last_price > open_price: up_count += 1
                elif last_price < open_price: down_count += 1
                else: flat_count += 1
                
                ticker_map[item['instId']] = {'price': last_price, 'change_pct': change_pct, 'vol_usd': float(item.get('volCcy24h', 0)) * last_price}

        total_contracts = up_count + down_count + flat_count
        market_breadth = {
            "up": up_count, "down": down_count, "flat": flat_count, "total": total_contracts,
            "up_pct": round((up_count / total_contracts) * 100, 1) if total_contracts else 0,
            "down_pct": round((down_count / total_contracts) * 100, 1) if total_contracts else 0,
            "flat_pct": round((flat_count / total_contracts) * 100, 1) if total_contracts else 0
        }

        oi_res = requests.get("https://www.okx.com/api/v5/public/open-interest?instType=SWAP", headers=HEADERS, timeout=10).json().get('data', [])
        valid_pairs = []
        btc_oi = eth_oi = btc_vol = eth_vol = 0
        
        for item in oi_res:
            inst_id = item.get('instId', '')
            if inst_id not in ticker_map: continue
            symbol = inst_id.split('-')[0]
            price = ticker_map[inst_id]['price']
            change_pct = ticker_map[inst_id]['change_pct']
            vol_usd = ticker_map[inst_id]['vol_usd']
            oi_usd = float(item.get('oiCcy', 0)) * price
            
            if symbol == 'BTC': btc_oi = oi_usd; btc_vol = vol_usd
            elif symbol == 'ETH': eth_oi = oi_usd; eth_vol = vol_usd
                
            if oi_usd > 5000000:  
                ratio = vol_usd / oi_usd if oi_usd > 0 else 0
                valid_pairs.append({
                    "symbol": symbol, 
                    "price": f"${price:.4f}" if price < 1 else f"${price:.2f}",
                    "change": f"+{change_pct:.2f}%" if change_pct > 0 else f"{change_pct:.2f}%",
                    "change_raw": change_pct,
                    "oi": f"${oi_usd / 1e6:.1f}M", 
                    "ratio": f"{ratio:.2f}"
                })
        
        valid_pairs.sort(key=lambda x: float(x['ratio']), reverse=True)
        
        return {
            "btc_oi": f"${btc_oi / 1e9:.2f}B", "btc_vol": f"${btc_vol / 1e9:.2f}B", "btc_ratio": f"{btc_vol / btc_oi:.2f}" if btc_oi else "N/A",
            "eth_oi": f"${eth_oi / 1e9:.2f}B", "eth_vol": f"${eth_vol / 1e9:.2f}B", "eth_ratio": f"{eth_vol / eth_oi:.2f}" if eth_oi else "N/A",
            "top_oi_movers": valid_pairs[:5], "market_breadth": market_breadth
        }
    except:
        return fallback_data

def generate_ai_insight(fgi, btc_funding, mb, btc_ratio):
    try:
        if fgi <= 15: return {"icon": "🩸", "title": "極度恐慌", "text": f"市場情緒指數僅 {fgi}，處於極度冰點。歷史經驗顯示，此處流動性匱乏，需留意莊家惡意插針洗盤後出現超跌反彈。"}
        
        if btc_funding != "N/A":
            funding_val = float(btc_funding.replace('+', '').replace('%', ''))
            if funding_val > 0.015: return {"icon": "🔥", "title": "多頭過熱", "text": f"BTC 資金費率達 {btc_funding}，做多槓桿成本顯著偏高。合約市場多頭擁擠，需警惕下殺清算多頭的風險。"}
            elif funding_val < -0.01: return {"icon": "🧊", "title": "空頭強勢", "text": f"BTC 資金費率為 {btc_funding}，呈現深度負值。市場作空情緒濃厚，若現貨跌不下去，極易醞釀暴力軋空行情。"}
        
        if mb.get('down_pct', 0) > 70: return {"icon": "📉", "title": "絕對弱勢", "text": f"全市場高達 {mb['down_pct']}% 的合約處於下跌狀態。大盤缺乏賺錢效應，建議降低部位風險，多看少做。"}
        elif mb.get('up_pct', 0) > 70: return {"icon": "🚀", "title": "全面爆發", "text": f"全市場 {mb['up_pct']}% 合約上漲。多頭動能強勁，資金正在全面擴散，可積極關注右側交易機會。"}
        
        if btc_ratio != "N/A":
            ratio_val = float(btc_ratio)
            if ratio_val > 10: return {"icon": "⚡", "title": "高頻換手", "text": f"BTC 持倉活躍度達 {ratio_val}x。24H 成交量遠超總持倉，短線資金博弈極度激烈，即將迎來方向性選擇。"}
            
        return {"icon": "⚖️", "title": "市場震盪", "text": "目前各項核心指標處於中性區間，多空雙方勢均力敵。建議控制倉位，等待更明確的右側信號出現。"}
    except: return {"icon": "🤖", "title": "數據分析中", "text": "等待足夠的市場數據以生成 AI 解讀..."}

if __name__ == "__main__":
    try:
        print("正在獲取市場數據...")
        tz_tpe = timezone(timedelta(hours=8))
        current_time = datetime.now(tz_tpe).strftime("%Y-%m-%d %H:%M:%S")
        
        btc_price = get_crypto_price("bitcoin")
        eth_price = get_crypto_price("ethereum")
        fgi_data = get_fear_and_greed_index()
        stablecoins = get_stablecoin_mcap()
        deriv_data = get_derivatives_data()
        btc_funding = get_funding_rate("BTC")
        
        ai_insight = generate_ai_insight(fgi_data["value"], btc_funding, deriv_data["market_breadth"], deriv_data["btc_ratio"])

        data = {
            "update_time": current_time,
            "btc_price": f"${btc_price:,}" if isinstance(btc_price, (int, float)) else btc_price,
            "eth_price": f"${eth_price:,}" if isinstance(eth_price, (int, float)) else eth_price,
            "fgi_value": fgi_data["value"], "fgi_classification": fgi_data["classification"],
            "btc_funding": btc_funding, "eth_funding": get_funding_rate("ETH"),
            "usdt_mcap": stablecoins["usdt"], "usdc_mcap": stablecoins["usdc"],
            "top_movers": get_top_movers(),
            "btc_oi": deriv_data["btc_oi"], "btc_vol": deriv_data["btc_vol"], "btc_ratio": deriv_data["btc_ratio"],
            "eth_oi": deriv_data["eth_oi"], "eth_vol": deriv_data["eth_vol"], "eth_ratio": deriv_data["eth_ratio"],
            "top_oi_movers": deriv_data["top_oi_movers"], "mb": deriv_data["market_breadth"],
            "ai": ai_insight, 
            "cb_premium": "****", 
            "btc_options_text": get_options_data("BTC"), 
            "eth_options_text": get_options_data("ETH"), 
            "btc_liq_text": "**** (待串接)", "eth_liq_text": "**** (待串接)"
        }

        env = Environment(loader=FileSystemLoader(os.path.dirname(os.path.abspath(__file__)) or '.'))
        template = env.get_template('template.html')
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(template.render(data))
        print("✅ 真實數據版網頁生成成功！")
    except Exception as e:
        print(f"❌ 發生嚴重錯誤: {e}")
        exit(1)
