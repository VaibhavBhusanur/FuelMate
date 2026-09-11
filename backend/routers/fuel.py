from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json
import ssl
from urllib.request import Request, urlopen

from database import SessionLocal
from models import Vehicle

router = APIRouter(prefix="/fuel", tags=["Fuel"])
# ============================================
# STATE-WISE PETROL REFERENCE PRICES
# ============================================

FUEL_PRICES = {
    "andaman and nicobar islands": 88.66,
    "andhra pradesh": 117.73,
    "arunachal pradesh": 99.69,
    "assam": 106.76,
    "bihar": 115.06,
    "chhattisgarh": 109.73,
    "goa": 104.13,
    "gujarat": 101.83,
    "haryana": 103.32,
    "himachal pradesh": 108.64,
    "jammu and kashmir": 106.35,
    "jharkhand": 105.43,
    "karnataka": 111.79,
    "kerala": 113.74,
    "madhya pradesh": 115.85,
    "maharashtra": 111.78,
    "manipur": 106.87,
    "meghalaya": 101.92,
    "mizoram": 106.81,
    "nagaland": 103.67,
    "odisha": 110.32,
    "punjab": 105.56,
    "rajasthan": 112.31,
    "sikkim": 103.30,
    "tamil nadu": 108.95,
    "telangana": 117.06,
    "tripura": 96.70,
    "uttar pradesh": 101.67,
    "uttarakhand": 102.16,
    "west bengal": 114.28,

    # Union Territories
    "delhi": 102.12,
    "chandigarh": 101.54,
    "puducherry": 103.37,
    "dadra and nagar haveli and daman and diu": 99.70,
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class FuelUpdate(BaseModel):
    vehicle_id: int
    fuel_level: float

# ============================================
# GET PETROL PRICE FROM CURRENT LOCATION
# ============================================

@router.get("/price")
def get_fuel_price(lat: float, lon: float):

    try:
        url = (
            "https://nominatim.openstreetmap.org/reverse"
            f"?format=json&lat={lat}&lon={lon}&zoom=5&addressdetails=1"
        )

        request = Request(
            url,
            headers={
                "User-Agent": "FuelMate/1.0"
            }
        )

        with urlopen(request, timeout=10, context=ssl._create_unverified_context()) as response:
            location_data = json.loads(
                response.read().decode("utf-8")
            )

        address = location_data.get("address", {})

        state = address.get("state")

        if not state:
            raise HTTPException(
                status_code=404,
                detail="Could not determine your state."
            )

        state_key = state.strip().lower()

        price = FUEL_PRICES.get(state_key)

        if price is None:
            raise HTTPException(
                status_code=404,
                detail=f"Fuel price not available for {state}."
            )

        return {
            "state": state,
            "fuel_type": "petrol",
            "price_per_litre": price
        }

    except HTTPException:
        raise

    except Exception as e:
        print("FUEL PRICE ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    
@router.get("/{vehicle_id}")
def get_fuel(vehicle_id: int, db: Session = Depends(get_db)):

    vehicle = db.query(Vehicle).filter(
        Vehicle.id == vehicle_id
    ).first()

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found"
        )

    fuel = float(vehicle.current_fuel or 0.0)

    return {
        "vehicle_id": vehicle.id,
        "fuel_level": fuel
    }


@router.post("/update")
def update_fuel(
    data: FuelUpdate,
    db: Session = Depends(get_db)
):

    if data.fuel_level < 0:
        raise HTTPException(
            status_code=400,
            detail="Fuel cannot be negative"
        )

    vehicle = db.query(Vehicle).filter(
        Vehicle.id == data.vehicle_id
    ).first()

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found"
        )

    if data.fuel_level > vehicle.tank_capacity:
        raise HTTPException(
            status_code=400,
            detail=f"Fuel cannot exceed tank capacity of {vehicle.tank_capacity} L"
        )

    vehicle.current_fuel = data.fuel_level

    db.commit()
    db.refresh(vehicle)

    return {
        "message": "Fuel updated successfully",
        "vehicle_id": vehicle.id,
        "fuel_level": float(vehicle.current_fuel)
    }