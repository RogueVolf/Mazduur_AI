import requests

def get_instagram_metrics(business_account_id, access_token):
    url = f"https://graph.facebook.com/v11.0/{business_account_id}/insights"
    
    params = {
        'metric': 'impressions,reach,profile_views,follower_count',
        'access_token': access_token
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        return f"Error: Unable to retrieve data. {e}"

    data = response.json()
    return format_metrics(data)

def format_metrics(data):
    metrics = data.get('data', [])
    report = "Instagram Business Account Metrics Report:\n\n"
    for metric in metrics:
        report += f"{metric['title']}:\n"
        for value in metric['values']:
            report += f"  {value['end_time']}: {value['value']}\n"
    return report

# Eg
business_account_id = "yoaccour_business_unt_id"
access_token = "your_access_token"

report = get_instagram_metrics(business_account_id, access_token)
print(report)
