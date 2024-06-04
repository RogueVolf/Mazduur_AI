#!pip install gspread oauth2client

import requests
import logging
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

logging.basicConfig(level=logging.INFO)

ACCESS_TOKEN = 'your_access_token'
BUSINESS_ACCOUNT_ID = 'your_business_account_id'
SPREADSHEET_ID = 'your_spreadsheet_id'
SERVICE_ACCOUNT_FILE = 'path_to_your_service_account_json_file.json'

def get_instagram_follower_count(business_account_id, access_token):
    """Retrieve the follower count for the business account."""
    api_version = 'v18.0'
    api_url = f'https://graph.facebook.com/{api_version}/{business_account_id}?fields=followers_count&access_token={access_token}'

    try:
        response = requests.get(api_url)
        response.raise_for_status()  
        data = response.json()
        follower_count = data['followers_count']
        logging.info(f'Instagram Follower Count: {follower_count}')
        return follower_count
    except requests.exceptions.RequestException as e:
        logging.error(f'Error occurred: {e}')
        return None

def get_instagram_insights(business_account_id, access_token, metrics, start_date, end_date):
    """Retrieve Instagram insights for the given metrics and date range."""
    api_version = 'v18.0'
    api_url = f'https://graph.facebook.com/{api_version}/{business_account_id}/insights'
    params = {
        'metric': ','.join(metrics),
        'period': 'day',
        'access_token': access_token,
        'since': int(start_date.timestamp()),
        'until': int(end_date.timestamp())
    }

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()['data']
        logging.info(f'Instagram Insights: {data}')

        # For Processing previous page if available
        if 'paging' in data and 'previous' in data['paging']:
            previous_page_url = data['paging']['previous']
            previous_page_data = fetch_previous_page(previous_page_url)
            write_to_spreadsheet(previous_page_data)
            log_insights(previous_page_data)

        return data
    except requests.exceptions.RequestException as e:
        logging.error(f'Error occurred: {e}')
        return None

def fetch_previous_page(previous_page_url):
    try:
        response = requests.get(previous_page_url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f'Error occurred: {e}')
        return None

def write_to_spreadsheet(data):
    """Write Instagram insights data to a Google Sheet."""
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1

    # Header and Data here
    headers = ['Metric', 'Value', 'End Time']
    rows = []

    for metric in data.get('data', []):
        for value in metric.get('values', []):
            rows.append([metric['title'], value['value'], value['end_time']])

    sheet.clear()
    sheet.append_row(headers)
    
    for row in rows:
        sheet.append_row(row)
    
    logging.info(f'Data written to Google Sheet: {SPREADSHEET_ID}')

def log_insights(data):
    for metric in data.get('data', []):
        logging.info(f"{metric['title']}:")
        for value in metric.get('values', []):
            logging.info(f"  Value: {value['value']}")
            logging.info(f"  End Time: {value['end_time']}")
        logging.info('-----')

def generate_report(follower_count, insights):
    """Generate a string report from the Instagram metrics."""
    report = f'Instagram Follower Count: {follower_count}\n\nInstagram Insights:\n'
    for metric in insights:
        report += f"{metric['title']}:\n"
        for value in metric['values']:
            report += f"  - Value: {value['value']}, End Time: {value['end_time']}\n"
    return report

# Eg
try:
    follower_count = get_instagram_follower_count(BUSINESS_ACCOUNT_ID, ACCESS_TOKEN)
    metrics = ['impressions', 'reach', 'profile_views', 'website_clicks']
    yesterday = datetime.now() - timedelta(days=1)
    insights = get_instagram_insights(BUSINESS_ACCOUNT_ID, ACCESS_TOKEN, metrics, yesterday, yesterday)
    report = generate_report(follower_count, insights)
    print(report)
except Exception as e:
    print(e)
