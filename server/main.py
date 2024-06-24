import os
import sys
import base64
from fastapi import FastAPI,Response,Path,Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing_extensions import Annotated,Tuple,Dict,Union,List
from typing import Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Column, Integer, String, DateTime
import datetime
import pickle as pk
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
import traceback

from models import ClientID_Table,Base,LastUpdate
from helper import use_llm

app = FastAPI()

def get_base_path():
    if getattr(sys, 'frozen', False):
        # The application is bundled
        return sys._MEIPASS
    else:
        # The application is not bundled
        return os.path.dirname(__file__)


def get_database_url():
    base_path = get_base_path()
    db_path = os.path.join(base_path,'db', 'auto_db.sqlite')
    return f"sqlite:///{db_path}"


DATABASE_URL = get_database_url()


engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

#==========================================HELPER_TOOLS============================================
# Function to load a public key from a PEM file
def load_public_key(filename : Annotated[str,"The filepath to client's public key"]
                    ) -> Annotated[RSAPublicKey,"The public key of the client"]:
    """
    Load a public key from a PEM file.

    Args:
        filename (str): The path to the PEM file containing the public key.

    Returns:
        RSAPublicKey: The loaded RSA public key object.
    """
    with open(filename, "rb") as f:
        public_key_bytes = f.read()
        public_key = serialization.load_pem_public_key(
            public_key_bytes,
            backend=default_backend()
        )
    return public_key

# Function to encrypt data using the public key
def encrypt_data(data : Annotated[str,"The data to be encrypted"],
                 public_key: Annotated[RSAPublicKey,"The public key of the client"]
                  ) -> Annotated[bytes,"The encoded string"]:
    """
    Encrypt a data using a client's public key

    Args:
        data (str): The data that needs to be encoded
        public_key (RSAPublicKey): The public key of the client
    
    Returns:
        bytes: The encoded data byte string
    """
    encrypted_data = public_key.encrypt(
        data.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return encrypted_data

#Function to classify dm
def classify_dm(message : Annotated[str,"The message that the user sent"]
                ) -> Annotated[str,"The classification for the message"]:
    """
    Classifies a DM sent to a client

    Args:
        message (str): The message received by the client

    Returns
        str: The class label of the message
                Casual: A normal message not enquiring about any product
                Intent: A message that might have a mention of any product or item name
                Desire: A message that may contain more details than just the name of the item or shows high desire to buy something
                Order: A message that conveys that the user has ordered an item already or sending details to process an order
                Collaboration: A message that may indicate that the user wants to collaborate on some project or deal     
    """
    
    try:
        response = use_llm(
            f"""
    The following message is from a person on instagram. I want you to classify this message for my business
    There are five classes in which you can put this message in
    Casual: A normal message not enquiring about any product
    Intent: A message that might have a mention of any product or item name
    Desire: A message that may contain more details than just the name of the item or shows high desire to buy something
    Order: A message that conveys that the user has ordered an item already or sending details to process an order
    Collaboration: A message that may indicate that the user wants to collaborate on some project or deal

    The user message is: {message}

    Your answer must only be the class and nothing else
    """
        )

        response = response.lower()
        print(response)
        if 'casual' in response:
            return 'Casual'
        elif 'intent' in response:
            return 'Intent'
        elif 'desire' in response:
            return 'Desire'
        elif 'order' in response:
            return 'Order'
        elif 'collaboration' in response:
            return 'Collaboration'
        else:
            return 'None'
    except Exception as e:
        print(e)
        return 'None'

# Function to check if a client ID exists
def client_id_exists(client_id: Annotated[str,"The new client ID"]) -> Annotated[bool,"Id exist status"]:
    """
    Checks if a client id exists in the DB or not

    Args:
        client_id (str): The client's id

    Returns:
        bool: True if the id exists or False
    """
    # Query the client_tables table for the client_id
    query = session.query(ClientID_Table).filter(
        ClientID_Table.client_id == client_id).first()
    return query is not None

#Function to get the dms a client has received
def get_dm_details(client_id : Annotated[str, "The client ID"]
                   ) -> Annotated[Union[List[Dict[str, Any]], str],"Returns dictionary of rows or error string"]:
    """
    Get all the DMs that a client has received in a given time

    Args:
        client_id (str): The id of the client

    Returns:
        Union[List[Dict[str, Any]], str]: The function can either return
            A list of dictionary with each dictionary having the user, message, intent and timestamp
            
            or
            
            A string telling what error happened
    """
    try:
        session = Session()
        client = session.query(ClientID_Table).filter(ClientID_Table.client_id == client_id).first()
        data_bin = None
        with open(client.bin_name,'rb') as file:
            data_bin = pk.load(file)
        row_details = [{
            'insta_id': base64.b64encode(row['insta_id']).decode('utf-8'),
            'message': base64.b64encode(row['message']).decode('utf-8'),
            'intent': base64.b64encode(row['intent']).decode('utf-8'),
            'timestamp': row['timestamp'].strftime("%d-%m-%y %H:%M:%S.%f")[:-3]
        } for row in data_bin]
        print(row_details)
        session.close()
        return row_details
    except Exception as e:
        return f"Failed due to {e}"

#Function to clear the dm details
def clear_dm_details(client_id: Annotated[str, "The client ID"]
                     ) -> Annotated[Tuple[bool, str], "A tuple with status and message"]:
    """
    Clears the server copy of all the DMs that the client id received

    Args:
        client_id (str): The id of the client

    Returns
        Tuple[bool,str]: It returns either
            True,"Successful" if the clearing was done successfully

            or

            False,"Error mesage" if the clearing was unsuccessful and the error message
    """
    try:
        session = Session()
        client = session.query(ClientID_Table).filter(
            ClientID_Table.client_id == client_id).first()
        data_bin = []
        with open(client.bin_name,'wb') as file:
            pk.dump(data_bin,file)
        session.close()
        return True,"Success"
    except Exception as e:
        return False,f"Failed due to {e}"
    
#============================================FASTAPI===============================================
class Client_Details(BaseModel):
    client_name: Annotated[str,"The client name"]
    client_id: Annotated[str,"The client id"]
    business_name: Annotated[str,"The business name"]

class DM_Details(BaseModel):
    insta_id : Annotated[str,"The instagram id of the user who sent the message"]
    message : Annotated[str,"The message the instagram id user has sent"]

@app.post('/create_client',response_class=JSONResponse,description="Creates a new client in the DB")
async def create_client(body:Client_Details = Body(...,description="The client details to enter")):
    try:
        session = Session()
        client = ClientID_Table(
            client_id = body.client_id,
            client_name = body.client_name,
            business_name = body.business_name,
            bin_name = f'./db/data_bins/{body.client_id}.data',
            key_name = f'./db/public_keys/{body.client_id}.pem'
        )

        data_bin = []
        with open(client.bin_name,'wb') as file:
            pk.dump(data_bin,file)

        session.add(client)
        session.commit()
        session.close()

        content = {'message':'Success'}

        return JSONResponse(content=content,status_code=200)
    except Exception as e:
        content = {'failed':f"{e}"}
        
        return JSONResponse(content=content,status_code=500)


@app.post('/new_dm/{client_id}',response_class=JSONResponse,description="Adds a new DM into the DB")
async def new_dm(client_id:str = Path(...,description="The client id who got the message"),
                 body:DM_Details = Body(...,description = "The DM details captured by the API")):
    try:
        session = Session()
        if not client_id_exists(client_id):
            content = {"failed": f"Client Does not Exist, Please Contact Admin"}
            return JSONResponse(content=content, status_code=404)
        else:
            client = session.query(ClientID_Table).filter(
                ClientID_Table.client_id == client_id).first()
            databin = None
            with open(client.bin_name,'rb') as file:
                databin = pk.load(file)
            
            client_public_key = load_public_key(client.key_name)

            #classify the dm
            classification = classify_dm(body.message)


            databin.append(
                {
                    'insta_id' : encrypt_data(body.insta_id,client_public_key),
                    'message' : encrypt_data(body.message,client_public_key),
                    'intent' : encrypt_data(classification,client_public_key),
                    'timestamp': datetime.datetime.now()
                }
            )

            with open(client.bin_name,'wb') as file:
                pk.dump(databin,file)

            content = {"message": "Success"}
            return JSONResponse(content=content, status_code=200)
    
    except Exception as e:
        traceback.print_exc()
        content = {"failed" : f"Failed in new_dm due to {e}"}
        return JSONResponse(content=content,status_code=500)

 
@app.get('/copy_dms/{client_id}',response_class=JSONResponse,description="Returns all the DM of a client and clears them in the server")
async def copy_dms(client_id:str = Path(...,description="The client id requesting updates")):
    try:   
        session = Session()
        current_time = datetime.datetime.now()
        last_update_record = session.query(LastUpdate).filter(LastUpdate.client_id == client_id).first()
        if last_update_record is None:
            last_update = LastUpdate(client_id = client_id,last_updated_time = current_time)
            session.add(last_update)
            session.commit()
            last_update_record = session.query(LastUpdate).filter(LastUpdate.client_id == client_id).first()

        last_update_record.last_updated_time = current_time
        session.commit()
        row_details = get_dm_details(client_id)
        status,message = clear_dm_details(client_id)

        if not status:
            content = {'failed': f"While deleting {message}"}
            return JSONResponse(content=content,status_code=500)
        
        content = {'db_details':row_details}
        return JSONResponse(content=content,status_code=200)
        
    except Exception as e:
        content = {'failed':f"In main {e}"}
        return JSONResponse(content=content,status_code=500)
    



