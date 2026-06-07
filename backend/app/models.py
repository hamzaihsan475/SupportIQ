from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from .database import Base

class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    location = Column(String, index=True)
    area = Column(Float)
    property_type = Column(String)
    price = Column(Float)
    bedrooms = Column(Integer)
    bathrooms = Column(Integer)
    status = Column(String, default="available")
    agency_id = Column(Integer, default=1, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    budget = Column(Float)
    contact = Column(String)
    agency_id = Column(Integer, default=1, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    role = Column(String)
    message = Column(String)
    status = Column(String, default="active")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )