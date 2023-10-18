from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from db_info import SystemInfo

class dbSqlAlchemy():
  
    def get_engine():
        dbuser = SystemInfo.dbuser
        dbpassword = SystemInfo.dbpassword
        host = SystemInfo.host
        dbname = SystemInfo.dbname
        
        engine = create_engine(
            "postgresql://"+dbuser+":"+dbpassword+"@"+host+":5432/"+dbname
        )

        base = declarative_base()

        Session = sessionmaker(engine)
        session = Session()

        base.metadata.create_all(engine)

        return engine,session