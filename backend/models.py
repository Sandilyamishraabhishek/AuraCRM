from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base

class HCP(Base):
    __tablename__ = "hcps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    specialty = Column(String, index=True)
    clinic = Column(String)
    email = Column(String)
    phone = Column(String)

    interactions = relationship("Interaction", back_populates="hcp", cascade="all, delete-orphan")

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id", ondelete="CASCADE"), nullable=False)
    interaction_type = Column(String, nullable=False)  # Meeting, Email, Call, Video, etc.
    date = Column(String, nullable=False)  # YYYY-MM-DD
    time = Column(String, nullable=False)  # HH:MM
    attendees = Column(Text)  # Comma separated list of names
    topics_discussed = Column(Text)
    sentiment = Column(String)  # Positive, Neutral, Negative
    outcomes = Column(Text)
    follow_up_actions = Column(Text)  # Comma-separated or JSON list of tasks
    materials_shared = Column(Text)  # Comma-separated list of material names
    samples_distributed = Column(Text)  # Comma-separated list of sample names

    hcp = relationship("HCP", back_populates="interactions")

class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    type = Column(String, nullable=False)  # "Sample" or "Material"
    stock = Column(Integer, default=100)
