from sqlalchemy import create_engine, Column, Integer, String, Float, Date, BLOB, DateTime
from sqlalchemy.ext.declarative import declarative_base
from helper import get_database_url
import datetime

DATABASE_URL = get_database_url()
# Define the database connection
engine = create_engine(DATABASE_URL, echo=True)
Base = declarative_base()


class ClientID_Table(Base):
    __tablename__="Client_ID_Table"

    id = Column(Integer,primary_key=True,autoincrement=True)
    client_id = Column(String,unique=True)
    client_name = Column(String)
    business_name = Column(String)
    table_name = Column(String,unique=True)


class LastUpdate(Base):
    __tablename__ = "Last_Update_Record"

    id = Column(Integer,primary_key=True,autoincrement=True)
    client_id = Column(String,unique=True)
    last_updated_time = Column(DateTime, nullable=False, default=datetime.datetime.now)


# Create the database tables
Base.metadata.create_all(engine)

