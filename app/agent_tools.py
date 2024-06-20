from typing_extensions import Annotated
import requests
import json
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import traceback

from tools import recognize_speech,speak_text,use_llm
from db_tools import insert_item,get_item_details,update_item

env_path = "D:/ABRAR/1_PERSONAL/Wolf_Tech/Mazduur_AI/app/.env"
load_dotenv(env_path)

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

def find_product(search_query: Annotated[str,"The product search query"]) -> Annotated[str,"The search results formatted"]:
    """
        This tool takes a search query for a product to find

        Parameters:
            search_query (str): The search query to gather information about a product

        Returns
            str: A paragraph with the top 5 sellers found for that product
    """
    

    modified_search_query = search_query + ' -site:amazon.com -site:justdial.com -site:amazon.in'


    url = "https://google.serper.dev/search"

    payload = json.dumps({
        "q": modified_search_query,
        # get this when setting up client account
        "location": "Bengaluru, Karnataka, India",
        "gl": "in",
        "num": 5
    })
    headers = {
        'X-API-KEY': os.environ['SERPER_KEY'],
        'Content-Type': 'application/json'
    }
    try:
        response = requests.request("POST", url, headers=headers, data=payload)

        values = response.json()["organic"]

        links_to_scrape = [x['link'] for x in values]

        information = ""

        for i,url in enumerate(links_to_scrape):
            data = requests.get(url)
            soup = BeautifulSoup(data.content, 'html.parser')
            # Extract and clean the body text
            body_text = soup.get_text()
            cleaned_text = ' '.join(body_text.split())[:10000]

            information += f'Seller {i+1}\n\nWebsite: {url}' + use_llm(f"""
                                {cleaned_text}
                                This is the data from a website for the following search key
                                {search_query}

                                You are an expert data analyst, summarise this website data in maximum five points.
                                The details should be oriented for a small startup founder and should include import details like MOQ, Price, Location of seller,Contact of the seller
                                Focus on providing information that fulfills the query.
                                The answer should be formatted in the following manner, no additional content but this particular format

                                Seller Name:
                                Product Description:
                                MOQ and Price:
                                Seller Contact:
                                Seller Location:
                                """) + '\n\n\n'

        with open('app/Data/Seller_Details_2.txt', 'w', encoding="utf-8") as file:
            file.write(information)

        return information
    except Exception as e:
        traceback.print_exc()
        return f"Exception {e}"
    