import os
import sys
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


from models import ClientID_Table,Base,LastUpdate

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
    print(f"Database path: {db_path}")
    return f"sqlite:///{db_path}"


DATABASE_URL = get_database_url()


engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

#==========================================HELPER_TOOLS============================================
# Function to load a public key from a PEM file
def load_public_key(filename):
    with open(filename, "rb") as f:
        public_key_bytes = f.read()
        public_key = serialization.load_pem_public_key(
            public_key_bytes,
            backend=default_backend()
        )
    return public_key

# Function to encrypt data using the public key
def encrypt_data(data, public_key):
    encrypted_data = public_key.encrypt(
        data.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    print(encrypted_data)
    return encrypted_data

#===========================================DB_TOOLS===============================================
# Function to check if a client ID exists
def client_id_exists(client_id: Annotated[str,"The new client ID"]) -> Annotated[bool,"True if it exists"]:
    # Query the client_tables table for the client_id
    query = session.query(ClientID_Table).filter(
        ClientID_Table.client_id == client_id).first()
    return query is not None


def get_dynamic_table(client_id: Annotated[str, "The client ID"]):
    table_name = f"client_{client_id}"
    return type(table_name, (Base,), {
        '__tablename__': table_name,
        'id': Column(Integer, primary_key=True, autoincrement=True),
        'message': Column(String, nullable=False),
        'sender': Column(String, nullable=False),
        'timestamp': Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    })

# # Function to create a data bin for a client ID
# def create_databin_for_client(client_id: Annotated[str,"The new client ID"]
#                             ) -> Annotated[Tuple[bool,str],"A tuple with True if it executes and status message"]:
#     try:
#         data_bin = []

#         with open(f'./db/data_bins/{client_id}.pkl','wb') as file:
#             pk.dump(data_bin,file)

#         return (True,'Successful')

#     except Exception as e:
#         return (False,f"Error {e}")
    

def get_db_details(client_id : Annotated[str, "The client ID"]
                   ) -> Annotated[Union[List[Dict[str, Any]], str],"Returns dictionary of rows or error string"]:
    try:
        session = Session()
        table_name = f"client_{client_id}"
        client_dm_table = type(table_name, (Base,), {
            '__tablename__': table_name,
            'id': Column(Integer, primary_key=True, autoincrement=True),
            'message': Column(String, nullable=False),
            'sender': Column(String, nullable=False),
            'timestamp': Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
        })

        # Checking if table already exists and using extend_existing if necessary
        if table_name in Base.metadata.tables:
            client_dm_table.__table__.extend_existing = True
        rows = session.query(client_dm_table).all()
        row_details = [{"id": row.id, "message": row.message,
                        "sender": row.sender, "timestamp": row.timestamp} for row in rows]
        session.close()
        return row_details
    except Exception as e:
        return f"Failed due to {e}"


def clear_db_details(client_id: Annotated[str, "The client ID"]
                     ) -> Annotated[Tuple[bool, str], "A tuple with True if it executes and status message"]:
    try:
        session = Session()
        table_name = f"client_{client_id}"
        client_dm_table = type(table_name, (Base,), {
            '__tablename__': table_name,
            'id': Column(Integer, primary_key=True, autoincrement=True),
            'message': Column(String, nullable=False),
            'sender': Column(String, nullable=False),
            'timestamp': Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
        })

        # Checking if table already exists and using extend_existing if necessary
        if table_name in Base.metadata.tables:
            client_dm_table.__table__.extend_existing = True

        session.query(client_dm_table).delete()
        session.commit()
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

@app.post('/create_client',response_class=JSONResponse)
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


@app.post('/new_dm/{client_id}',response_class=JSONResponse)
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

            databin.append(
                {
                    'insta_id' : encrypt_data(body.insta_id,client_public_key),
                    'message' : encrypt_data(body.message,client_public_key),
                    'timestamp' : datetime.datetime.now()
                }
            )

            with open(client.bin_name,'wb') as file:
                pk.dump(databin,file)

            content = {"message": "Success"}
            return JSONResponse(content=content, status_code=200)
    
    except Exception as e:
        content = {"failed" : f"Failed in new_dm due to {e}"}
        return JSONResponse(content=content,status_code=500)

 
@app.get('/update_dms/{client_id}',response_class=JSONResponse)
async def update_dms(client_id:str = Path(...,description="The client id requesting updates")):
    session = Session()
    last_update_record = session.query(LastUpdate).filter(LastUpdate.client_id == client_id).first()
    last_update_time = last_update_record.last_updated_time
    current_time = datetime.datetime.now()
    if last_update_time < current_time:
        last_update_record.last_updated_time = current_time
        row_details = get_db_details(client_id)
        status,message = clear_db_details(client_id)

        if not status:
            content = {'failed': message}
            return JSONResponse(content=content,status_code=500)
        
        content = {'db_details':row_details}
        return JSONResponse(content=content,status_code=200)
    
    else:
        content = {'db_details':'DB up to date'}
        return JSONResponse(content=content,status_code=204)