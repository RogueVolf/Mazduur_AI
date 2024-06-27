import requests
import json
import time

EMAIL = 'meloidasdragneel12@gmail.com'
PASSWORD = 'manishghoshal99'
BASE_URL = 'https://apiv2.shiprocket.in/v1/external'
LOGIN_URL = f'{BASE_URL}/auth/login'
ORDER_URL = f'{BASE_URL}/orders/create/adhoc'
TRACK_URL = f'{BASE_URL}/courier/track'
APPLICATION_URL = 'https://your-application.com/api/order-status'  

def generate_token(email, password):
    login_payload = {
        "email": email,
        "password": password
    }
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(LOGIN_URL, headers=headers, data=json.dumps(login_payload))
    if response.status_code == 200:
        return response.json().get('token')
    else:
        print("Failed to generate token:", response.text)
        return None

def place_order(order_data, token):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    response = requests.post(ORDER_URL, json=order_data, headers=headers)
    if response.status_code == 200:
        order_response = response.json()
        return order_response.get('shipment_id')
    else:
        print("Failed to place order:", response.text)
        return None

def track_order(tracking_id, token):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    response = requests.get(f'{TRACK_URL}/{tracking_id}', headers=headers)
    if response.status_code == 200:
        tracking_response = response.json()
        return tracking_response
    else:
        print("Failed to track order:", response.text)
        return None
def push_order_status(order_status, application_url):
    response = requests.post(application_url, json=order_status)
    if response.status_code == 200:
        print("Order status pushed successfully")
    else:
        print("Failed to push order status:", response.text)


order_data = {
    "id": 5155981,
    "name": "CUSTOM",
    "status": "Active",
    "connection_response": None,
    "channel_updated_at": "2024-06-22 08:05:03",
    "status_code": 1,
    "settings": {
        "dimensions": "0x0x0",
        "weight": 0,
        "order_status": ""
    },
    "auth": [],
    "connection": 1,
    "orders_sync": 0,
    "inventory_sync": 0,
    "catalog_sync": 0,
    "orders_synced_on": "Not Available",
    "inventory_synced_on": "Not Available",
    "base_channel_code": "CS",
    "base_channel": {
        "id": 4,
        "name": "MANUAL",
        "code": "CS",
        "type": "Carts",
        "logo": "custom.png",
        "settings_sample": {
            "name": "Channels Settings",
            "help": "",
            "settings": {
                "brand_name": {
                    "code": "brand_name",
                    "name": "Brand Name",
                    "placeholder": "Your brand name",
                    "type": "text"
                },
                "brand_logo": {
                    "code": "brand_logo",
                    "name": "Brand Logo",
                    "placeholder": "Your brand logo",
                    "type": "file"
                }
            }
        },
        "auth_sample": [],
        "description": "Manual channel"
    },
    "catalog_synced_on": "26 Jun, 11:59 AM",
    "order_status_mapper": "",
    "payment_status_mapper": "",
    "brand_name": "",
    "brand_logo": "",
    "brand_id": 0,
    "allow_mark_as_paid": False,
    "warehouse_locations": [],
    "skip_unpaid_prepaid": False,
    "vendor_id": 0,
    "b2b_channels": []
}


def main():
    token = generate_token(EMAIL, PASSWORD)
    if not token:
        return
    
    shipment_id = place_order(order_data, token)
    if shipment_id:
        print("Order placed successfully, Shipment ID:", shipment_id)
        
        time.sleep(10)
        
        order_status = track_order(shipment_id, token)
        if order_status:
            print("Order status:", order_status)
            
            push_order_status(order_status, APPLICATION_URL)
        else:
            print("Failed to get order status")
    else:
        print("Failed to place order")

if __name__ == "__main__":
    main()
