import os
import json
import asyncio
import aiohttp
import aiofiles
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

BASE_URL = 'https://apiv2.shiprocket.in/v1/external'
LOGIN_URL = f'{BASE_URL}/auth/login'
FORWARD_SHIPMENT_URL = f'{BASE_URL}/shipments/create/forward-shipment'
RETURN_SHIPMENT_URL = f'{BASE_URL}/shipments/create/return-shipment'
APPLICATION_URL = os.getenv('APPLICATION_URL')

class ShiprocketOrderProcessor:
    def __init__(self):
        self.email = os.getenv('SHIPROCKET_EMAIL')
        self.password = os.getenv('SHIPROCKET_PASSWORD')
        self.token = None
        if not self.email or not self.password:
            raise ValueError("Shiprocket credentials not found in environment variables")

    async def login(self):
        """Authenticate and get the token."""
        async with aiohttp.ClientSession() as session:
            async with session.post(LOGIN_URL, json={
                "email": self.email,
                "password": self.password
            }) as response:
                data = await response.json()
                self.token = data.get('token')
                if not self.token:
                    raise ValueError("Failed to obtain authentication token")

    async def process_order(self, order_data: Dict[str, Any], is_return: bool = False) -> Dict[str, Any]:
        if not self.token:
            await self.login()

        if is_return:
            validation_errors = self.validate_return_order_data(order_data)
            shipment_url = RETURN_SHIPMENT_URL
        else:
            validation_errors = self.validate_forward_order_data(order_data)
            shipment_url = FORWARD_SHIPMENT_URL

        if validation_errors:
            return {"status": "error", "message": "Validation failed", "errors": validation_errors}

        # Create shipment
        shipment_result = await self.create_shipment(order_data, shipment_url)
        
        if shipment_result.get("status") == 1:
            payload = shipment_result["payload"]
            order_id = payload["order_id"]
            
            if not is_return:
                await self.store_urls(order_id, payload.get("label_url"), payload.get("manifest_url"))
            
            await self.update_order_status(payload)
            
            return {
                "status": "success",
                "message": f"{'Return' if is_return else 'Forward'} order processed successfully",
                "order_id": order_id,
                "shipment_id": payload["shipment_id"],
                "awb_code": payload["awb_code"],
                "courier_name": payload["courier_name"],
                "label_url": payload.get("label_url"),
                "manifest_url": payload.get("manifest_url")
            }
        else:
            return {"status": "error", "message": f"Failed to create {'return' if is_return else 'forward'} shipment", "details": shipment_result}

    def validate_forward_order_data(self, data: Dict[str, Any]) -> List[str]:
        """Validate the forward order data before sending to Shiprocket."""
        errors = []
        required_fields = [
            "order_id", "order_date", "pickup_location", "channel_id", "billing_customer_name",
            "billing_address", "billing_city", "billing_pincode", "billing_state", "billing_country",
            "billing_email", "billing_phone", "order_items", "payment_method", "sub_total",
            "length", "breadth", "height", "weight"
        ]

        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")

        if "order_items" in data and isinstance(data["order_items"], list):
            for item in data["order_items"]:
                if not all(key in item for key in ["name", "sku", "units", "selling_price"]):
                    errors.append("Missing required fields in order_items")
                    break
        else:
            errors.append("Invalid or missing order_items")

        return errors

    def validate_return_order_data(self, data: Dict[str, Any]) -> List[str]:
        """Validate the return order data before sending to Shiprocket."""
        errors = []
        required_fields = [
            "order_id", "order_date", "channel_id", "pickup_customer_name",
            "pickup_address", "pickup_city", "pickup_state", "pickup_country",
            "pickup_pincode", "pickup_email", "pickup_phone",
            "shipping_customer_name", "shipping_address", "shipping_city",
            "shipping_state", "shipping_country", "shipping_pincode",
            "shipping_email", "shipping_phone", "order_items", "payment_method",
            "sub_total", "length", "breadth", "height", "weight"
        ]

        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")

        if "order_items" in data and isinstance(data["order_items"], list):
            for item in data["order_items"]:
                if not all(key in item for key in ["name", "sku", "units", "selling_price"]):
                    errors.append("Missing required fields in order_items")
                    break
        else:
            errors.append("Invalid or missing order_items")

        return errors

    async def create_shipment(self, order_data: Dict[str, Any], url: str) -> Dict[str, Any]:
        """Create a shipment using Shiprocket API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=order_data, headers=headers) as response:
                return await response.json()

    async def store_urls(self, order_id: str, label_url: str, manifest_url: str) -> None:
        """Store label and manifest URLs in files within an order-specific directory."""
        order_dir = os.path.join("orders", str(order_id))
        os.makedirs(order_dir, exist_ok=True)

        async def save_url(filename: str, url: str):
            if url:
                filepath = os.path.join(order_dir, filename)
                async with aiofiles.open(filepath, mode='w') as f:
                    await f.write(url)

        await asyncio.gather(
            save_url("label_url.txt", label_url),
            save_url("manifest_url.txt", manifest_url)
        )

    async def update_order_status(self, order_data: Dict[str, Any]) -> None:
        """Update the order status in your application."""
        async with aiohttp.ClientSession() as session:
            async with session.post(APPLICATION_URL, json=order_data) as response:
                if response.status != 200:
                    print(f"Failed to update order status. Status code: {response.status}")

async def process_orders_from_file(filename: str) -> List[Dict[str, Any]]:
    """Process orders from a JSON file."""
    processor = ShiprocketOrderProcessor()
    
    async with aiofiles.open(filename, mode='r') as f:
        content = await f.read()
        orders = json.loads(content)
    
    results = []
    for order in orders:
        is_return = order.get("is_return", False)
        result = await processor.process_order(order, is_return)
        results.append(result)
    
    return results

async def main():
    results = await process_orders_from_file('orders.json')
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
