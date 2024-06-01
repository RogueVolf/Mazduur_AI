from tools import recognize_speech,speak_text
from db_tools import insert_item,get_item_details,update_item
from typing_extensions import Annotated

def insert_item_to_db() -> Annotated[bool,"True if the item was added successfully, False if not"]:
    """
        This tool adds an item to the database after taking input from the user
        
        Returns:
            True: if the addition was a success
            False: if the addition was not successful
    """

    speak_text("What is the product name")
    product_name = recognize_speech()
    speak_text("What is the image file name")
    image_file = recognize_speech()
    speak_text("What is the cost of the product")
    cost_price = float(recognize_speech())
    speak_text("What is the selling price of the product")
    selling_price = float(recognize_speech())
    speak_text("How many units of the product do you have")
    units = int(recognize_speech())

    result = insert_item(product_name,image_file,cost_price,selling_price,units)

    return result

def view_item(product_name:Annotated[str,"The product name"]) -> Annotated[str,"The product details"]:
    """
        This tool takes a product name and returns all the details about the product

        Returns:
            str: A string that contains all the product details
    """
    result = get_item_details(product_name)

    return result

def update_item_in_db(product_name: Annotated[str,"The product name"]) -> Annotated[bool,"True if successfully updated or else False"]:
    """
        This tool takes the product name and updates the required field with a new value

        Returns:
            True: If the update was successful
            False: If the update was unsuccessful
    """
    speak_text("What field do you want to update")
    field_name = recognize_speech()
    speak_text("What is the new value")
    new_value = recognize_speech()

    if field_name in ['cost','selling_price']:
        new_value = float(new_value)
    elif field_name in ['units']:
        new_value = int(new_value)

    result = update_item(product_name,field_name,new_value)

    return result
