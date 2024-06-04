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
    questions = {
        'product': "What is the product name",
        'cost_price': "What is the cost of the product",
        'selling_price': "What is the selling price of the product",
        'units': "How many units of the product do you have"
    }

    answers = {}
    for question in questions.keys():
        correct = "No"
        value = ""
        while(correct!="yes"):
            speak_text(questions[question])
            value = recognize_speech()
            speak_text(f"You replied {value}, tell yes if correct")
            correct = recognize_speech()
        if question == "units":
            value = int(value)
        elif question in ['cost_price','selling_price']:
            value = float(value)

        answers[question] = value

    result = insert_item(answers['product'],'None',answers['cost_price'],answers['selling_price'],answers['units'])
    if result:
        speak_text(f"Inserted {answers['product']} successfully")
        return result
    else:
        speak_text("""Could not insert product
                   Please try again""")
        return result

def view_item(product_name:Annotated[str,"The product name"]) -> Annotated[str,"The product details"]:
    """
        This tool takes a product name and returns all the details about the product

        Returns:
            str: A string that contains all the product details
    """
    result = get_item_details(product_name)
    speak_text(result)
    return result

def update_units(product_name: Annotated[str,"The product name"],new_units: Annotated[int,"The number of units to change to"]) -> Annotated[bool,"True if successfully updated or else False"]:
    """
        This tool takes the product name and updates the units field with the new_units value

        Returns:
            True: If the update was successful
            False: If the update was unsuccessful
    """
    if not isinstance(new_units,int):
        speak_text("Please tell me an integer value for the units")
        return False
    result = update_item(product_name.lower(),'units',new_units)
    if result:
        speak_text(f"Updated {product_name} units successfully to {new_units}")
        return result
    else:
        speak_text("Could not update value due to some error please try again")
        return result


def update_cost_price(product_name: Annotated[str, "The product name"], new_cp: Annotated[float, "The new cost price of the product"]) -> Annotated[bool, "True if successfully updated or else False"]:
    """
        This tool takes the product name and updates the cost price field with the new_cp value

        Returns:
            True: If the update was successful
            False: If the update was unsuccessful
    """
    if not isinstance(new_cp, float):
        speak_text("Please tell me a correct value for the cost price")
        return False
    result = update_item(product_name.lower(), 'cost', new_cp)
    if result:
        speak_text(f"Updated {product_name} cost price successfully to {new_cp}")
        return result
    else:
        speak_text("Could not update value due to some error please try again")
        return result


def update_selling_price(product_name: Annotated[str, "The product name"], new_sp: Annotated[float, "The new selling price of the product"]) -> Annotated[bool, "True if successfully updated or else False"]:
    """
        This tool takes the product name and updates the selling price field with the new_sp value

        Returns:
            True: If the update was successful
            False: If the update was unsuccessful
    """
    if not isinstance(new_sp, float):
        speak_text("Please tell me a correct value for the cost price")
        return False
    result = update_item(product_name.lower(), 'selling_price', new_sp)
    if result:
        speak_text(
            f"Updated {product_name} selling price successfully to {new_sp}")
        return result
    else:
        speak_text("Could not update value due to some error please try again")
        return result
