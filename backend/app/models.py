from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
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
    # Valid status string values: "pending", "approved", "rejected", "deleted".
    # "deleted" is a soft-delete flag — the row is preserved for audit/history.
    status = Column(String, default="approved")
    agency_id = Column(Integer, default=1, nullable=False)
    submitter_name = Column(String, nullable=True)
    submitter_contact = Column(String, nullable=True)
    is_sold = Column(Boolean, default=False)

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