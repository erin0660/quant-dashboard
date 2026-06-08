import requests
from jinja2 import Template
from datetime import datetime

def generate_dashboard():
    print("正在連線獲取最新市場數據...")
    
    # === 1. 真實 API 數據抓取 ===
    try:
        # 抓取 BTC 與 ETH 價格
        cg_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
        prices = requests.get(cg_url).json()
        btc_price = f"{prices['bitcoin']['usd']:,.0f}"
        eth_price = f"{prices['ethereum']['usd']:,.0f}"
        
        # 抓取恐懼貪婪指數
        fg_res = requests.get("https://api.alternative.me/fng/").json()
        fng_value = fg_res['data'][0]['value']
        fng_class = fg_res['data'][0]['value_classification']
    except Exception as e:
        print("API 抓取失敗:", e)
        return

    # === 2. 準備所有要填入網頁的資料 (包含未來的擴充欄位) ===
    data_payload = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        
        # 真實數據
        "btc_price": btc_price,
        "eth_price": eth_price,
        "fng_value": fng_value,
        "fng_class": fng_class,
        
        # 以下為模擬數據 (未來接上 API 後直接替換這裡的值即可)
        "dxy_value": "100.11",
        "gold_value": "4,359.1 (-0.14%)",
        "tga_value": "844,521 M (-1,201)",
        "usdt_mcap": "187.03 B",
        "usdt_flow": "-146.88 M (24h)",
        "usdc_mcap": "75.58 B",
        "usdc_vol": "0.1464",
        "btc_funding": "+0.00367%",
        "cb_premium": "-0.047%",
        "btc_exchange_flow": "-4,403.17",
        "btc_lth": "16.35 M",
        "eth_funding": "-0.00966%",
        "eth_exchange_flow": "-269.95 K",
        "eth_top100": "89.54%",
        "eth_entry": "3,024,096 ETH",
        "eth_wait": "52天 12小時",
        "eth_exit": "23,246 ETH",
        "btc_oi": "711.36K ($44.97B)",
        "btc_oi_change": "+1.20%",
        "btc_vol_oi": "0.57",
        "eth_oi": "14.44M ($24.35B)",
        "eth_oi_change": "+4.19%",
        "btc_options": "260626 到期日名義金額現峰值 ($9.00B)，最大痛點達 $75.0K。",
        "eth_options": "260925 最大痛點折線達峰值 (接近 $2.4K)。",
        "btc_liq": f"現價 ${btc_price}。下方 61,040 - 63,252 區間有顯著多單清算密集區。",
        "eth_liq": f"現價 ${eth_price}。上方累積極龐大空單清算強度，峰值突破 10.00B。"
    }

    # === 3. 讀取模板並合成 ===
    with open(r"template.html", "r", encoding="utf-8") as f:
        template_content = f.read()

    template = Template(template_content)
    final_html = template.render(**data_payload) # 將字典裡的所有資料一次塞進去

    # === 4. 產出最終網頁 ===
    output_path = r"專業量化日報.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"✅ 成功！已生成完整的量化日報：{output_path}")

if __name__ == "__main__":
    generate_dashboard()
