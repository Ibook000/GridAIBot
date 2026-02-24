import requests
url = 'https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT'
resp = requests.get(url).json()
data = resp['data'][0] if resp.get('data') else {}
print(f'【波动提醒】BTC 当前价格: {data.get("last", "N/A")} USDT，请注意看盘！')