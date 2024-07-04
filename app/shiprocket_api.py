import asyncio
import logging
import os
from typing import Dict, Any, Optional, List, Callable
import aiohttp
from dotenv import load_dotenv
from ratelimit import limits, sleep_and_retry
load_dotenv()

BASE_URL = 'https://apiv2.shiprocket.in/v1/external'
LOGIN_URL = f'{BASE_URL}/auth/login'
SHIPMENT_URL = f'{BASE_URL}/shipments/create/forward-shipment'
RETURN_ORDER_URL = f'{BASE_URL}/orders/create/return'
TRACK_URL = f'{BASE_URL}/courier/track'
APPLICATION_URL = os.getenv('APPLICATION_URL', 'https://your-application.com/api/order-status')


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ShiprocketAPI:
    def __init__(self):
        self.session = None
        self.token = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.generate_token()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    @sleep_and_retry
    @limits(calls=2, period=1)  # Rate limit: 2 calls per second
    async def generate_token(self) -> None:
        email = os.getenv('SHIPROCKET_EMAIL')
        password = os.getenv('SHIPROCKET_PASSWORD')
        if not email or not password:
            raise ValueError("Shiprocket credentials not found in environment variables")

        login_payload = {"email": email, "password": password}
        headers = {'Content-Type': 'application/json'}

        try:
            async with self.session.post(LOGIN_URL, json=login_payload, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                self.token = data.get('token')
                if not self.token:
                    raise ValueError("Token not found in API response")
        except aiohttp.ClientError as e:
            logger.error(f"Failed to generate token: {e}")
            raise

    @sleep_and_retry
    @limits(calls=2, period=1)  # Rate limit: 2 calls per second
    async def make_api_request(self, url: str, method: str, data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        if not self.token:
            await self.generate_token()

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }

        try:
            async with getattr(self.session, method.lower())(url, json=data, headers=headers) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {e}")
            if response.status == 401:  # IF EXPIRED RIP 
                await self.generate_token()
                return await self.make_api_request(url, method, data)  # Retry with new token
            return None

    async def create_shipment(self, shipment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        response = await self.make_api_request(SHIPMENT_URL, 'POST', shipment_data)
        return response.get('payload') if response else None

    async def create_return_order(self, return_order_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return await self.make_api_request(RETURN_ORDER_URL, 'POST', return_order_data)

    async def track_order(self, tracking_id: str) -> Optional[Dict[str, Any]]:
        return await self.make_api_request(f'{TRACK_URL}/{tracking_id}', 'GET')

async def push_order_status(order_status: Dict[str, Any]) -> None:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(APPLICATION_URL, json=order_status) as response:
                response.raise_for_status()
                logger.info("Order status pushed successfully")
        except aiohttp.ClientError as e:
            logger.error(f"Failed to push order status: {e}")

def validate_data(data: Dict[str, Any], required_fields: List[str], additional_checks: Dict[str, Callable] = None) -> Dict[str, str]:
    errors = {}
    for field in required_fields:
        if field not in data or not data[field]:
            errors[field] = f"Missing required field: {field}"

    if additional_checks:
        for field, check_func in additional_checks.items():
            if field in data:
                error = check_func(data[field])
                if error:
                    errors[field] = error

    return errors

def validate_order_items(items: List[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(items, list):
        return "order_items must be a list"
    for item in items:
        if not all(key in item for key in ['name', 'sku', 'units', 'selling_price']):
            return "Missing required fields in order_items"
    return None

def validate_payment_method(method: str) -> Optional[str]:
    if method not in ['PREPAID', 'COD']:
        return "Invalid payment method. Must be either 'PREPAID' or 'COD'"
    return None

def validate_pincode(pincode: Any) -> Optional[str]:
    if not isinstance(pincode, int):
        return "Pincode must be an integer"
    return None

def validate_shipment_data(data: Dict[str, Any]) -> Dict[str, str]:
    required_fields = [
        'order_id', 'order_date', 'channel_id', 'billing_customer_name',
        'billing_address', 'billing_city', 'billing_pincode', 'billing_state',
        'billing_country', 'billing_email', 'billing_phone', 'order_items',
        'payment_method', 'sub_total', 'length', 'breadth', 'height', 'weight'
    ]
    return validate_data(data, required_fields, {
        'order_items': validate_order_items,
        'payment_method': validate_payment_method
    })

def validate_return_order_data(data: Dict[str, Any]) -> Dict[str, str]:
    required_fields = [
        'order_id', 'order_date', 'channel_id', 'pickup_customer_name', 'pickup_address',
        'pickup_city', 'pickup_state', 'pickup_country', 'pickup_pincode', 'pickup_email',
        'pickup_phone', 'shipping_customer_name', 'shipping_address', 'shipping_city',
        'shipping_country', 'shipping_pincode', 'shipping_state', 'shipping_phone',
        'order_items', 'payment_method', 'sub_total', 'length', 'breadth', 'height', 'weight'
    ]
    return validate_data(data, required_fields, {
        'order_items': validate_order_items,
        'payment_method': validate_payment_method,
        'pickup_pincode': validate_pincode,
        'shipping_pincode': validate_pincode
    })

async def process_order(api: ShiprocketAPI, order_data: Dict[str, Any], is_return: bool = False) -> Optional[Dict[str, Any]]:
    validation_func = validate_return_order_data if is_return else validate_shipment_data
    create_order_func = api.create_return_order if is_return else api.create_shipment
    order_type = "return order" if is_return else "shipment"

    validation_errors = validation_func(order_data)
    if validation_errors:
        logger.error(f"Validation errors for {order_type}:")
        for field, error in validation_errors.items():
            logger.error(f"- {field}: {error}")
        return None

    order_result = await create_order_func(order_data)
    if order_result:
        logger.info(f"{order_type.capitalize()} created successfully: {order_result}")
        
        await asyncio.sleep(10)  
        
        shipment_id = order_result.get('shipment_id')
        if shipment_id:
            order_status = await api.track_order(shipment_id)
            if order_status:
                logger.info(f"Order status: {order_status}")
                await push_order_status(order_status)
            else:
                logger.error("Failed to get order status")
        else:
            logger.error(f"No shipment ID found in {order_type} result")
        
        return order_result
    else:
        logger.error(f"Failed to create {order_type}")
        return None

async def main():
    
    shipment_data = {
        "order_id": "22114477",
        "order_date": "2024-07-03 12:23",
        "channel_id": "27202",
        "billing_customer_name": "Jax",
        "billing_last_name": "Tank",
        "billing_address": "Dust2",
        "billing_city": "New Delhi",
        "billing_pincode": "110002",
        "billing_state": "Delhi",
        "billing_country": "India",
        "billing_email": "jax@counterstike.com",
        "billing_phone": "9988998899",
        "shipping_is_billing": True,
        "order_items": [
            {
                "name": "T-shirt Round Neck",
                "sku": "t-shirt-round1474",
                "units": 10,
                "selling_price": "400"
            }
        ],
        "payment_method": "COD",
        "sub_total": 4000,
        "length": 100,
        "breadth": 50,
        "height": 10,
        "weight": 0.50,
        "pickup_location": "HomeNew",
        "vendor_details": {
            "email": "abcdd@abcdd.com",
            "phone": 9879879879,
            "name": "Coco Cookie",
            "address": "Street 1, Near ABC Road",
            "address_2": "",
            "city": "delhi",
            "state": "new delhi",
            "country": "india",
            "pin_code": "110077",
            "pickup_location": "HomeNew"
        }
    }

    
    return_order_data = {
        "order_id": "r121579B09ap3o",
        "order_date": "2024-07-03",
        "channel_id": "27202",
        "pickup_customer_name": "iron man",
        "pickup_last_name": "",
        "company_name": "iron pvt ltd",
        "pickup_address": "b 123",
        "pickup_address_2": "",
        "pickup_city": "Delhi",
        "pickup_state": "New Delhi",
        "pickup_country": "India",
        "pickup_pincode": 110030,
        "pickup_email": "deadpool@red.com",
        "pickup_phone": "9810363552",
        "pickup_isd_code": "91",
        "shipping_customer_name": "Jax",
        "shipping_last_name": "Doe",
        "shipping_address": "Castle",
        "shipping_address_2": "Bridge",
        "shipping_city": "ghaziabad",
        "shipping_country": "India",
        "shipping_pincode": 201005,
        "shipping_state": "Uttarpardesh",
        "shipping_email": "kumar.abhishek@shiprocket.com",
        "shipping_isd_code": "91",
        "shipping_phone": 8888888888,
        "order_items": [
            {
                "name": "shoes",
                "qc_enable": True,
                "qc_product_name": "shoes",
                "sku": "WSH234",
                "units": 1,
                "selling_price": 100,
                "discount": 0,
                "qc_brand": "Levi",
                "qc_product_image": "https://assets.vogue.in/photos/5d7224d50ce95e0008696c55/2:3/w_2240,c_limit/Joker.jpg"
            }
        ],
        "payment_method": "PREPAID",
        "total_discount": "0",
        "sub_total": 400,
        "length": 11,
        "breadth": 11,
        "height": 11,
        "weight": 0.5
    }

    async with ShiprocketAPI() as api:
       
        logger.info("Processing forward shipment:")
        shipment_result = await process_order(api, shipment_data)

        
        customer_wants_return = True  
        if shipment_result and customer_wants_return:
            logger.info("Processing return order:")
            await process_order(api, return_order_data, is_return=True)

if __name__ == "__main__":
    asyncio.run(main())

# test_shiprocket_api.py
import pytest
from unittest.mock import patch, AsyncMock
from main import ShiprocketAPI, validate_shipment_data, validate_return_order_data

@pytest.fixture
async def api():
    async with ShiprocketAPI() as api:
        yield api

@pytest.mark.asyncio
async def test_generate_token(api):
    with patch.object(api.session, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.__aenter__.return_value.json.return_value = {'token': 'test_token'}
        await api.generate_token()
        assert api.token == 'test_token'

@pytest.mark.asyncio
async def test_create_shipment(api):
    with patch.object(api, 'make_api_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {'payload': {'shipment_id': '123'}}
        result = await api.create_shipment({})
        assert result == {'shipment_id': '123'}

@pytest.mark.asyncio
async def test_create_return_order(api):
    with patch.object(api, 'make_api_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {'order_id': '456'}
        result = await api.create_return_order({})
        assert result == {'order_id': '456'}


@pytest.mark.asyncio
async def test_track_order(api):
    with patch.object(api, 'make_api_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {'tracking_data': {'status': 'In Transit'}}
        result = await api.track_order('123')
        assert result == {'tracking_data': {'status': 'In Transit'}}

def test_validate_shipment_data():
    valid_data = {
        'order_id': '123',
        'order_date': '2023-07-04',
        'channel_id': '456',
        'billing_customer_name': 'John Doe',
        'billing_address': '123 Main St',
        'billing_city': 'New York',
        'billing_pincode': '10001',
        'billing_state': 'NY',
        'billing_country': 'USA',
        'billing_email': 'john@example.com',
        'billing_phone': '1234567890',
        'order_items': [{'name': 'Item 1', 'sku': 'SKU1', 'units': 1, 'selling_price': 100}],
        'payment_method': 'PREPAID',
        'sub_total': 100,
        'length': 10,
        'breadth': 10,
        'height': 10,
        'weight': 1
    }
    assert validate_shipment_data(valid_data) == {}

    invalid_data = valid_data.copy()
    invalid_data.pop('order_id')
    errors = validate_shipment_data(invalid_data)
    assert 'order_id' in errors

def test_validate_return_order_data():
    valid_data = {
        'order_id': '123',
        'order_date': '2023-07-04',
        'channel_id': '456',
        'pickup_customer_name': 'John Doe',
        'pickup_address': '123 Main St',
        'pickup_city': 'New York',
        'pickup_state': 'NY',
        'pickup_country': 'USA',
        'pickup_pincode': 10001,
        'pickup_email': 'john@example.com',
        'pickup_phone': '1234567890',
        'shipping_customer_name': 'Jane Doe',
        'shipping_address': '456 Elm St',
        'shipping_city': 'Los Angeles',
        'shipping_country': 'USA',
        'shipping_pincode': 90001,
        'shipping_state': 'CA',
        'shipping_phone': '9876543210',
        'order_items': [{'name': 'Item 1', 'sku': 'SKU1', 'units': 1, 'selling_price': 100}],
        'payment_method': 'PREPAID',
        'sub_total': 100,
        'length': 10,
        'breadth': 10,
        'height': 10,
        'weight': 1
    }
    assert validate_return_order_data(valid_data) == {}

    invalid_data = valid_data.copy()
    invalid_data['pickup_pincode'] = '10001'  
    errors = validate_return_order_data(invalid_data)
    assert 'pickup_pincode' in errors
