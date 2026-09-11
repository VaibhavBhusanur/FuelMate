from sqlalchemy.ext.mutable import MutableList
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

    rides = relationship("Ride", back_populates="user")
    vehicles = relationship("Vehicle", back_populates="owner")

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String, nullable=False)
    model = Column(String, nullable=False)
    year = Column(Integer)
    owner_id = Column(Integer, ForeignKey("users.id"))
    mileage = Column(Float, nullable=False)
    tank_capacity = Column(Float, nullable=False)
    current_fuel = Column(Float, default=0.0)

    owner = relationship("User", back_populates="vehicles")
    rides = relationship("Ride", back_populates="vehicle")

class Ride(Base):
    __tablename__ = "rides"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    start_fuel = Column(Float)
    fuel_remaining = Column(Float, default=0.0)
    fuel_used = Column(Float, default=0.0)
    distance = Column(Float, default=0.0)
    avg_speed = Column(Float, default=0.0)
    start_time = Column(
    DateTime,
    default=lambda: datetime.datetime.now(datetime.timezone.utc)
)
    end_time = Column(DateTime)

    odometer_start = Column(Float)
    locations = Column(MutableList.as_mutable(JSON), default=list)
    speed_samples = Column(MutableList.as_mutable(JSON), default=list)

    user = relationship("User", back_populates="rides")
    vehicle = relationship("Vehicle", back_populates="rides")
