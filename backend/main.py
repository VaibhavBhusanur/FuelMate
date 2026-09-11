# main.py
"""
FuelMate - main FastAPI entry

This file exposes:
- GET  /                 -> health / welcome
- POST /seed             -> (dev) create sample user + vehicle
- POST /start_ride       -> begin a ride (persisted)
- POST /update_location  -> periodic GPS pings (updates distance, fuel, avg speed)
- POST /end_ride         -> finish ride and return summary
- GET  /vehicles         -> list vehicles
- GET  /ride/{ride_id}   -> fetch ride details
"""

# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field # <-- Change this line to also import Field
from sqlalchemy.orm import Session
# ...
from typing import Optional, List, Any
import datetime
from math import radians, cos, sin, asin, sqrt

# Local imports (your database & models files)
from database import Base, engine, SessionLocal   # database.py should expose these
from models import User, Vehicle, Ride
Base.metadata.create_all(bind=engine)            # models.py should define these
from sqlalchemy import text

with engine.connect() as conn:
    columns = conn.execute(
        text("PRAGMA table_info(vehicles)")
    ).fetchall()

    column_names = [column[1] for column in columns]

    if "current_fuel" not in column_names:
        conn.execute(
            text(
                "ALTER TABLE vehicles "
                "ADD COLUMN current_fuel FLOAT DEFAULT 0.0"
            )
        )
        conn.commit()


# Global in-memory data store for fuel prices (Dev-only)
fuel_prices = {
    "karnataka": 101.5,
    "maharashtra": 106.2,
    "delhi": 96.7,
    "tamilnadu": 103.1
}

# Ensure DB tables exist (creates tables if missing)

app = FastAPI(title="FuelMate Backend (Full)")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # dev: allow all. For prod, restrict to your domains.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from routers import rides, vehicles, fuel, auth
app.include_router(rides.router)
app.include_router(vehicles.router)
app.include_router(fuel.router)
app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "FuelMate Backend (modular) — visit /docs to inspect API"}

# ----------------------------
# DB session dependency
# ----------------------------
def get_db():
    """
    Provide a database session to path operations.
    Use as: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------
# Utility: haversine distance
# ----------------------------
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Haversine formula to compute distance between two lat/lon points in kilometers.
    """
    R = 6371.0  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2.0) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2.0) ** 2
    c = 2 * asin(sqrt(a))
    return R * c

# ----------------------------
# Pydantic request/response schemas
# ----------------------------
class FuelPriceUpdate(BaseModel):
    state: str
    price: float

class AddVehicleRequest(BaseModel):
    user_id: int
    brand: str
    model: str
    year: Optional[int] = None
    mileage: Optional[float] = None
    tank_capacity: Optional[float] = None

class SeedIn(BaseModel):
    email: str = "test@local"
    name: str = "Test User"
    vehicle_brand: str = "Hero"
    vehicle_model: str = "Splendor"
    vehicle_year: Optional[int] = 2018
    vehicle_mileage: Optional[float] = 60.0
    vehicle_tank_capacity: Optional[float] = 8.0

class RideStartRequest(BaseModel):
    user_id: int
    vehicle_id: int
    fuel_filled_in_rs: float = Field(..., gt=0, description="Amount of fuel filled in Indian Rupees (INR).")
    state: str # Add this line
    lat: Optional[float] = None
    lon: Optional[float] = None

class RideStartResponse(BaseModel):
    ride_id: int
    message: str
    vehicle: str
    start_fuel: float
    fuel_price: float # Added to show the price used for calculation

class LocationUpdateRequest(BaseModel):
    ride_id: int
    latitude: float
    longitude: float
    speed: float | None = 0.0
    # If app reports tank gauge, send it; otherwise omit and we’ll estimate from mileage
    fuel_remaining: float | None = None

class RideUpdateResponse(BaseModel):
    ride_id: int
    message: str
    total_distance: float
    fuel_remaining: float
    avg_speed: float


class EndRideRequest(BaseModel):
    ride_id: int
    end_fuel: Optional[float] = None
class EndRideResponse(BaseModel):
    ride_id: int
    message: str
    vehicle: str
    mileage: float
    distance: float
    fuel_used: float
    fuel_left: float
    fuel_percent: float
    alert: Optional[str] = None


# ----------------------------
# Routes
# ----------------------------
@app.get("/")
def home():
    return {"message": "FuelMate FastAPI Backend Running 🚀"}

# ---------- Manual Fuel Price Update (Dev-only) ----------
@app.post("/update_fuel_price")
def update_fuel_price(payload: FuelPriceUpdate):
    """
    Manually updates the in-memory fuel price for a given state.
    Use for development purposes only.
    """
    state_lower = payload.state.lower()
    if payload.price <= 0:
        raise HTTPException(status_code=400, detail="Price must be a positive value.")

    fuel_prices[state_lower] = payload.price
    return {"message": f"Fuel price for {state_lower} updated successfully.", "new_price": payload.price}


# ---------- Seed (dev helper) ----------
@app.post("/seed")
def seed(data: SeedIn, db: Session = Depends(get_db)):
    """
    Development helper: create a user and a vehicle if they don't exist.
    Safe to call multiple times.
    """
    # user
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        user = User(name=data.name, email=data.email)
        db.add(user)
        db.commit()
        db.refresh(user)

    # vehicle
    v = db.query(Vehicle).filter(Vehicle.brand == data.vehicle_brand, Vehicle.model == data.vehicle_model, Vehicle.year == data.vehicle_year).first()
    if not v:
        v = Vehicle(
            brand=data.vehicle_brand,
            model=data.vehicle_model,
            year=data.vehicle_year,
            mileage=data.vehicle_mileage or 0.0,
            tank_capacity=data.vehicle_tank_capacity or 0.0
        )
        db.add(v)
        db.commit()
        db.refresh(v)

    return {"ok": True, "user_id": user.id, "vehicle_id": v.id}

# @app.post("/add_vehicle")
# def add_vehicle(payload: AddVehicleRequest, db: Session = Depends(get_db)):
#     """
#     Allows a user to add a new vehicle to their profile.
#     """
#     # 1. Check if the user exists
#     user = db.query(User).filter(User.id == payload.user_id).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     # 2. Check for an existing vehicle with the same details to prevent duplicates
#     existing_vehicle = db.query(Vehicle).filter(
#         Vehicle.owner_id == payload.user_id,
#         Vehicle.brand == payload.brand,
#         Vehicle.model == payload.model
#     ).first()
#     if existing_vehicle:
#         return {"message": "Vehicle already exists for this user", "vehicle_id": existing_vehicle.id}

#     # 3. Create the new vehicle object
#     new_vehicle = Vehicle(
#         owner_id=payload.user_id,
#         brand=payload.brand,
#         model=payload.model,
#         year=payload.year,
#         mileage=payload.mileage,
#         tank_capacity=payload.tank_capacity
#     )
#     db.add(new_vehicle)
#     db.commit()
#     db.refresh(new_vehicle)

#     return {"message": "Vehicle added successfully", "vehicle_id": new_vehicle.id}

# ---------- Start Ride ----------
#@app.post("/start_ride", response_model=RideStartResponse)
#def start_ride(payload: RideStartRequest, db: Session = Depends(get_db)):
#   user = db.query(User).filter(User.id == payload.user_id).first()
#    if not user:
 #       raise HTTPException(status_code=404, detail="User not found")
#
 #   vehicle = db.query(Vehicle).filter(Vehicle.id == payload.vehicle_id).first()
  #  if not vehicle:
   #     raise HTTPException(status_code=404, detail="Vehicle not found")
#
 #   # Step 1: Get fuel price from our in-memory dictionary
  #  state_lower = payload.state.lower()
   # price_per_litre = fuel_prices.get(state_lower)
#
 #   if not price_per_litre:
  #      raise HTTPException(status_code=400, detail=f"Fuel price for state '{state_lower}' not available. Please update it via the /update_fuel_price endpoint.")
#
 #   # Step 2: Calculate litres from Rupees
  #  litres_filled = payload.fuel_filled_in_rs / price_per_litre
#
 #   # Step 3: Create the ride entry in the database with the calculated litres
  #  ride = Ride(
   #     user_id=user.id,
    #    vehicle_id=vehicle.id,
     #   start_fuel=litres_filled, # Storing the litres, not Rs
      #  fuel_remaining=litres_filled,
       # fuel_used=0.0,
      #  distance=0.0,
       # avg_speed=0.0,
       # start_time=datetime.datetime.now(datetime.timezone.utc),
       # locations=[],
       # speed_samples=[],
    #)
  #  db.add(ride)
  #  db.commit()
  #  db.refresh(ride)

    # Append initial GPS ping if provided
    #if payload.lat is not None and payload.lon is not None:
    #    ride.locations.append([float(payload.lat), float(payload.lon)])
   #     db.add(ride)
  #      db.commit()
 #       db.refresh(ride)
#
    # Return the new response model with the calculated values
    #return {
    #    "ride_id": ride.id,
    #    "message": "Ride started",
   #     "vehicle": f"{vehicle.brand} {vehicle.model}",
  #      "start_fuel": litres_filled,
 #       "fuel_price": price_per_litre
#    }

# # ---------- Update Location ----------
# @app.post("/update_location", response_model=RideUpdateResponse)
# def update_location(payload: LocationUpdateRequest, db: Session = Depends(get_db)):
#     """
#     Receive periodic GPS pings.
#     - Append new (lat, lon) to locations
#     - Compute incremental distance via haversine
#     - Update fuel_used & fuel_remaining using vehicle mileage (unless client supplies fuel_remaining)
#     - Recompute average speed
#     """
#     # Fetch ride
#     ride = db.query(Ride).filter(Ride.id == payload.ride_id).first()
#     if not ride:
#         raise HTTPException(status_code=404, detail="Ride not found")

#     # Get vehicle to read rated mileage
#     vehicle = db.query(Vehicle).filter(Vehicle.id == ride.vehicle_id).first()
#     if not vehicle:
#         raise HTTPException(status_code=500, detail="Associated vehicle not found")

#     # Ensure JSON lists exist (avoid None)
#     locations = ride.locations or []
#     speed_samples = ride.speed_samples or []

#     # Calculate incremental distance if previous point exists
#     distance_inc = 0.0
#     if len(locations) >= 1:
#         prev_lat, prev_lon = float(locations[-1][0]), float(locations[-1][1])
#         distance_inc = haversine(prev_lat, prev_lon, float(payload.latitude), float(payload.longitude))
#         ride.distance = float(ride.distance or 0.0) + distance_inc

#     # Fuel usage estimate from vehicle mileage (km/l)
#     fuel_used_inc = 0.0
#     mileage_val = float(vehicle.mileage or 0.0)
#     if distance_inc > 0 and mileage_val > 0:
#         fuel_used_inc = distance_inc / mileage_val
#         ride.fuel_used = float(ride.fuel_used or 0.0) + fuel_used_inc

#     # If client provided current tank reading, use that; otherwise subtract the estimate
#     if payload.fuel_remaining is not None:
#         ride.fuel_remaining = max(0.0, float(payload.fuel_remaining))
#     else:
#         ride.fuel_remaining = max(0.0, float(ride.fuel_remaining or 0.0) - fuel_used_inc)

#     # Append latest point & speed
#     locations.append([float(payload.latitude), float(payload.longitude)])
#     speed_samples.append(float(payload.speed or 0.0))

#     # Recompute avg speed (simple mean)
#     ride.avg_speed = float(sum(speed_samples) / len(speed_samples)) if speed_samples else 0.0

#     # Persist JSON fields back
#     ride.locations = locations
#     ride.speed_samples = speed_samples

#     db.add(ride)
#     db.commit()
#     db.refresh(ride)

#     return {
#         "ride_id": ride.id,
#         "message": "Location updated",
#         "total_distance": round(float(ride.distance or 0.0), 3),
#         "fuel_remaining": round(float(ride.fuel_remaining or 0.0), 3),
#         "avg_speed": round(float(ride.avg_speed or 0.0), 2),
#     }


# ---------- End Ride ----------
# # ---------- End Ride ----------
# @app.post("/end_ride", response_model=EndRideResponse)
# def end_ride(payload: EndRideRequest, db: Session = Depends(get_db)):
#     """
#     End a ride and return summary.
#     - Uses odometer_end if present (and odometer_start exists) to compute distance.
#     - Uses end_fuel if provided to compute fuel_used (prefers client-provided).
#     - Otherwise uses recorded GPS distance and recorded fuel_used.
#     - Returns mileage, distance, fuel used, fuel left, fuel % and an alert if low.
#     """
#     # fetch ride
#     ride = db.query(Ride).filter(Ride.id == payload.ride_id).first()
#     if not ride:
#         raise HTTPException(status_code=404, detail="Ride not found")

#     # prevent double-ending
#     if getattr(ride, "end_time", None) is not None:
#         raise HTTPException(status_code=400, detail="Ride already ended")

#     # vehicle label (safe)
#     vehicle = db.query(Vehicle).filter(Vehicle.id == ride.vehicle_id).first()
#     vehicle_label = f"{vehicle.brand} {vehicle.model}" if vehicle else "Unknown"

#     # set end time (timezone-aware UTC)
#     ride.end_time = datetime.datetime.now(datetime.timezone.utc)

#     # 1) Distance: prefer odometer if both values available
#     distance_km = float(ride.distance or 0.0)

#     # 2) Fuel calculations
#     # a) gather start_fuel if present, else estimate from recorded values
#     start_fuel_val = None
#     if getattr(ride, "start_fuel", None) is not None:
#         try:
#             start_fuel_val = float(ride.start_fuel)
#         except Exception:
#             start_fuel_val = None

#     # If we don't have a stored start_fuel, try to estimate: used + remaining
#     if start_fuel_val is None:
#         try:
#             recorded_used = float(ride.fuel_used or 0.0)
#             recorded_remaining = float(ride.fuel_remaining or 0.0)
#             est = recorded_used + recorded_remaining
#             start_fuel_val = est if est > 0 else None
#         except Exception:
#             start_fuel_val = None

#     # b) if client provided end_fuel, use it to compute fuel_used and remaining
#     fuel_used = float(ride.fuel_used or 0.0)
#     if payload.end_fuel is not None:
#         try:
#             end_fuel_val = float(payload.end_fuel)
#             # compute fuel_used using start_fuel if we have it, else fallback to recorded usage
#             if start_fuel_val is not None:
#                 fuel_used = max(0.0, start_fuel_val - end_fuel_val)
#             else:
#                 # fallback: recorded fuel_used adjusted to match provided end_fuel if possible
#                 fuel_used = float(ride.fuel_used or 0.0)
#             ride.end_fuel = end_fuel_val
#             ride.fuel_used = fuel_used
#             ride.fuel_remaining = max(0.0, end_fuel_val)
#         except Exception:
#             # ignore conversion errors, keep recorded values
#             pass
#     else:
#         # no client end_fuel: use recorded fuel_used & fuel_remaining (already updated via pings)
#         fuel_used = float(ride.fuel_used or 0.0)

#     # final safety values
#     total_distance = float(distance_km or 0.0)
#     fuel_used = float(fuel_used or 0.0)
#     fuel_left = float(ride.fuel_remaining or 0.0)

#     # compute mileage (km per litre)
#     mileage = round((total_distance / fuel_used), 2) if fuel_used > 0 else 0.0

#     # fuel percent (relative to start fuel); guard division by zero
#     fuel_percent = 0.0
#     if start_fuel_val is not None and start_fuel_val > 0:
#         fuel_percent = round((fuel_left / start_fuel_val) * 100, 1)
#     else:
#         # if no start fuel info, try a sensible estimate (avoid NaN)
#         fuel_percent = 0.0

#     # alert rules
#     alert = None
#     if fuel_percent <= 10 and fuel_percent > 0:
#         alert = "Low fuel — refill soon"

#     # persist the final ride row
#     db.add(ride)
#     db.commit()
#     db.refresh(ride)

#     # return final summary (matches EndRideResponse)
#     return {
#         "ride_id": ride.id,
#         "message": "Ride ended successfully",
#         "vehicle": vehicle_label,
#         "mileage": mileage,
#         "distance": round(total_distance, 3),
#         "fuel_used": round(fuel_used, 3),
#         "fuel_left": round(fuel_left, 3),
#         "fuel_percent": fuel_percent,
#         "alert": alert
#     }

# ---------- List Vehicles ----------
# @app.get("/vehicles")
# def list_vehicles(db: Session = Depends(get_db)):
#     """
#     Return all vehicles in DB.
#     Useful for the frontend to populate the vehicle select list.
#     """
#     vehicles = db.query(Vehicle).all()
#     out = []
#     for v in vehicles:
#         out.append({
#             "id": v.id,
#             "brand": v.brand,
#             "model": v.model,
#             "year": getattr(v, "year", None),
#             "mileage": float(v.mileage) if v.mileage is not None else None,
#             "tank_capacity": float(v.tank_capacity) if v.tank_capacity is not None else None,
#         })
#     return out

# ---------- Get a ride (details) ----------
@app.get("/ride/{ride_id}")
def get_ride(ride_id: int, db: Session = Depends(get_db)):
    """
    Fetch stored ride details including location list and speed samples.
    """
    r = db.query(Ride).filter(Ride.id == ride_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="ride not found")

    return {
        "ride_id": r.id,
        "user_id": r.user_id,
        "vehicle_id": r.vehicle_id,
        "start_time": r.start_time.isoformat() if r.start_time else None,
        "end_time": r.end_time.isoformat() if getattr(r, "end_time", None) else None,
        "distance_km": float(r.distance or 0.0),
        "fuel_used": float(r.fuel_used or 0.0),
        "fuel_remaining": float(r.fuel_remaining or 0.0),
        "avg_speed": float(r.avg_speed or 0.0),
        "locations": r.locations or [],
        "speed_samples": r.speed_samples or []
    }
# ---------- Test Fuel Price ----------
@app.get("/test_fuel_price")
def test_fuel_price(state: str = "karnataka"):
    """
    Dummy fuel price fetcher (replace with real API later).
    Example: /test_fuel_price?state=karnataka
    """
    # This dictionary is now the global 'fuel_prices' from the previous step.
    # We will access the global 'fuel_prices' dictionary.

    # Step 1: Try to fetch price
    price = fuel_prices.get(state.lower())

    # Step 2: Return response
    if price:
        return {"state": state, "petrol_price": price}
    else:
        return {"state": state, "error": "Fuel price not available"}

