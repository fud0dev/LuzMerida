import requests
import json
import os
from datetime import datetime, timedelta

def scrape_electricity_prices():
    # Official ESIOS (REE) API for PVPC (Spain)
    # Archive 70 contains the aggregated PVPC prices (with taxes)
    date_str = datetime.now().strftime("%Y-%m-%d")
    url = f"https://api.esios.ree.es/archives/70/download_json?date={date_str}"
    
    data = None
    
    try:
        print(f"Fetching data from official ESIOS API: {url}")
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            raw_data = response.json()
            pvpc_list = raw_data.get('PVPC', [])
            
            if not pvpc_list:
                raise ValueError("No data found in ESIOS response")
                
            standardized = []
            prices_list = []
            
            for item in pvpc_list:
                # Hour format from ESIOS is "HH-HH"
                hour_start = int(item['Hora'].split('-')[0])
                # Price is in €/MWh in the field "PCB" (Peninsula, Canarias, Baleares)
                # We need to replace comma with dot for float conversion
                price_str = item['PCB'].replace(',', '.')
                price_mwh = float(price_str)
                price_kwh = price_mwh / 1000
                
                prices_list.append(price_kwh)
                standardized.append({
                    "hour": hour_start,
                    "price": round(price_kwh, 5),
                    # We will calculate flags after getting min/max
                    "isLow": False,
                    "isMid": False,
                    "isHigh": False
                })
            
            # Calculate thresholds for aesthetics (matching tarifaluzhora.es feel)
            min_p = min(prices_list)
            max_p = max(prices_list)
            range_p = max_p - min_p
            
            # 33% chunks for low/mid/high
            low_threshold = min_p + (range_p * 0.33)
            high_threshold = min_p + (range_p * 0.66)
            
            for item in standardized:
                if item['price'] <= low_threshold:
                    item['isLow'] = True
                elif item['price'] >= high_threshold:
                    item['isHigh'] = True
                else:
                    item['isMid'] = True
                    
            # Sort by hour
            standardized.sort(key=lambda x: x['hour'])
            data = standardized
            
        else:
            print(f"ESIOS API failed with status {response.status_code}")
    except Exception as e:
        print(f"Error fetching from ESIOS: {e}")

    # Fallback to a mock/old values only if everything fails completely
    if not data:
        print("Scraping failed. No data to save.")
        return

    # Metadata and Summary
    result = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prices": data,
        "summary": {
            "min": round(min(p['price'] for p in data), 5),
            "max": round(max(p['price'] for p in data), 5),
            "avg": round(sum(p['price'] for p in data) / len(data), 5)
        }
    }

    # Ensure output directory exists
    # If running in GitHub Actions, it might be docs/data
    output_path = 'docs/data/luz.json'
    if not os.path.exists('docs'):
        # Fallback for different execution contexts
        output_path = 'LuzMerida/docs/data/luz.json'
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully updated {output_path}")

if __name__ == "__main__":
    scrape_electricity_prices()
