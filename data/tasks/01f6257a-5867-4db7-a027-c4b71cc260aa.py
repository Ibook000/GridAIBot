import requests
url = 'https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP'
resp = requests.get(url).json()
data = resp['data'][0] if resp.get('data') else {}
current_rate = float(data.get('fundingRate', 0)) if data.get('fundingRate') else 0
next_rate = float(data.get('nextFundingRate', 0)) if data.get('nextFundingRate') else 0
print(f'''BTC-USDT 资金费率监控:
当前资金费率: {current_rate:.6f}
下次资金费率: {next_rate:.6f}
更新时间: {data.get('fundingTime', 'N/A')}''')