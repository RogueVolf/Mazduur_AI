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
    db_path = os.path.join(base_path, 'server','db', 'auto_db.sqlite')
    print(f"Database path: {db_path}")
    return f"sqlite:///{db_path}"


DATABASE_URL = get_database_url()

engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

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

# Function to create a dynamic table for a client ID
def create_table_for_client(client_id: Annotated[str,"The new client ID"]
                            ) -> Annotated[Tuple[bool,str],"A tuple with True if it executes and status message"]:
    try:
        # Define the table schema dynamically
        DynamicTable = get_dynamic_table(client_id)

        # Create the table in the database
        Base.metadata.create_all(engine)

        return (True,'Successful')

    except Exception as e:
        return (False,f"Error {e}")
    

def get_db_details(client_id : Annotated[str, "The client ID"]
                   ) -> Annotated[Union[List[Dict[str, Any]], str],"Returns dictionary of rows or error string"]:
    try:
        session = Session()
        client_dm_table = get_dynamic_table(client_id)
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
        client_dm_table = get_dynamic_table(client_id)
        session.query(client_dm_table).delete()
        session.commit()
        return True,"Success"
    except Exception as e:
        return False,f"Failed due to {e}"
    
#============================================FASTAPI===============================================

class DM_Details(BaseModel):
    insta_id : Annotated[str,"The instagram id of the user who sent the message"]
    message : Annotated[str,"The message the instagram id user has sent"]


@app.post('/new_dm/{client_id}',response_class=JSONResponse)
async def new_dm(client_id:str = Path(...,"The client id who got the message"),
                 body:DM_Details = Body(...,"The DM details captured by the API")):
    try:
        session = Session()
        if not client_id_exists(client_id):
            status,detail = create_table_for_client(client_id)
            if not status:
                content = {"failed": f"Failed due to {detail}"}
                return JSONResponse(content=content, status_code=500)
        
        #Inserting dm into a respective table if client table exists
        DynamicTable = type(f"client_{client_id}", (Base,), {
            '__tablename__': f"client_{client_id}",
            'id': Column(Integer, primary_key=True, autoincrement=True),
            'message': Column(String, nullable=False),
            'sender': Column(String, nullable=False),
            'timestamp': Column(DateTime, nullable=False, default=datetime.datetime.now)
        })

        dynamic_table_instance = DynamicTable(message=body.message, sender=body.insta_id)
        session.add(dynamic_table_instance)
        session.commit()
        session.close()
        content = {"message": "Success"}
        return JSONResponse(content=content, status_code=200)
    
    except Exception as e:
        content = {"failed" : f"Failed due to {e}"}
        return JSONResponse(content=content,status_code=500)

 
@app.get('/update_dms/{client_id}',response_class=JSONResponse)
async def update_dms(client_id:str = Path(...,"The client id requesting updates")):
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