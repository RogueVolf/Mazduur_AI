import pymongo
from typing_extensions import Annotated
from typing import Any
import random
import os
from dotenv import load_dotenv
env_path = "D:/ABRAR/1_PERSONAL/Wolf_Tech/Mazduur_AI/app/.env"
load_dotenv(env_path)

client = pymongo.MongoClient(os.environ["MONGO_DB_URI"])

db = client["Mazduur"]

collection = db["enfume_db"]

def insert_item(product : Annotated[str,"The name of the product"],
           image : Annotated[str,"The base64 string of the image"],
           cost : Annotated[float,"The cost of the product"],
           selling_price:Annotated[float,"The selling price of the product"],
           units : Annotated[int,"The number of product units"]) -> Annotated[bool,"True if successfully inserted or else False"]:
    """
        This function adds an item to the database after taking input from the user
        
        Returns:
            True: if the addition was a success
            False: if the addition was not successful
    """
    insert_entry = {
        '_id': ''.join(random.choices("0123456789", k=5)),
        'product' : product.lower(),
        'image' : image,
        'cost' : cost,
        'selling_price' : selling_price,
        'units' : units
    }

    try:
        collection.insert_one(insert_entry)
        return True 
    except Exception as e:
        print(f'Exception occured {e}')
        return False
    
def get_item_details(product:Annotated[str,"The name of the product"]) -> Annotated[str,"Details of the product"]:
    """
        This function takes a product name and returns all the details about the product

        Returns:
            str: A string that contains all the product details
    """
    query = {'product' : product.lower()}

    items = collection.find(query)

    final_string = ""
    
    if collection.count_documents(query) == 0:
        return "No product by that name"
        
    for item in items:
        final_string += f"""Product Details are the SKU is {item['_id']} for {item['product']} 
        The Cost Price is {item['cost']}
        Its selling at {item['selling_price']} 
        The number of Units left is {item['units']}\n"""

    return final_string


def update_item(product:Annotated[str,"The name of the product"],
                field:Annotated[str,"The field that needs to be updated"],
                new_value: Annotated[Any,"The new value to be entered"]) -> Annotated[bool,"True if successfully updated or else False"]:
    """
        This function takes the product name and updates the required field with a new value

        Returns:
            True: If the update was successful
            False: If the update was unsuccessful
    """

    query = {'product':product}
    updated_values = {"$set":{field:new_value}}

    try:
        result = collection.update_one(query, updated_values)
        if result.matched_count > 0:
            return True
        else:
            print(f"No document found with product name: {product}")
            return False
    except Exception as e:
        print(f"Exception happened: {e}")
        return False


