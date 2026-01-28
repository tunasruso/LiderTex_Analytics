from sqlalchemy import Column, Integer, String, Date, Numeric
from api.database import Base

class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    product = Column(String(100))
    amount = Column(Numeric(10, 2))
    region = Column(String(50))
