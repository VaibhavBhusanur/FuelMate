# backend/routers/rides.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Ride, Vehicle
import datetime
from math import radians, cos, sin, asin, sqrt
from typing import Optional
import requests



router = APIRouter(prefix="/rides", tags=["Rides"])

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Haversine helper (returns kilometers)
def haversine_km(lat1, lon1, lat2, lon2):
    # convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    R = 6371  # Radius of earth in kilometers.
    return c * R

# ---- GPS Filtering Rules ----
MIN_MOVEMENT_KM = 0.02
MAX_REALISTIC_SPEED = 180
MIN_SPEED_THRESHOLD = 3


# --------------------------
# Start Ride (improved)
# --------------------------
@router.post("/start")
def start_ride(data: dict, db: Session = Depends(get_db)):
    """
    Expects data: { user_id, vehicle_id, start_fuel (litres), odometer_start (optional) }
    """
    user_id = data.get("user_id")
    vehicle_id = data.get("vehicle_id")
    start_fuel = float(data.get("start_fuel", 0) or 0)
    odometer_start = float(data.get("odometer_start") or 0)

    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    new_ride = Ride(
        user_id=user_id,
        vehicle_id=vehicle_id,
        start_fuel=start_fuel,
        fuel_remaining=start_fuel,
        fuel_used=0.0,
        distance=0.0,
        avg_speed=0.0,
        start_time=datetime.datetime.now(datetime.timezone.utc),
        odometer_start=odometer_start,
        locations=[],        # list of {"lat":..., "lon":..., "ts": ISO}
        speed_samples=[]     # list of instantaneous speeds (km/h)
    )
    db.add(new_ride)
    db.commit()
    db.refresh(new_ride)
    return {"message": "Ride started", "ride_id": new_ride.id}

# --------------------------
# Update Location - main heartbeat
# --------------------------
@router.post("/update_location")
def update_location(data: dict, db: Session = Depends(get_db)):
    """
    Expects: { ride_id, lat, lon, timestamp (optional, ISO string) }
    Called frequently (e.g., every 5s) by frontend.
    """
    ride_id = data.get("ride_id")
    lat = data.get("lat")
    lon = data.get("lon")
    ts = data.get("timestamp")  # optional ISO string

    if not ride_id or lat is None or lon is None:
        raise HTTPException(status_code=400, detail="ride_id, lat and lon required")

    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    # parse timestamp or use now
    try:
        if ts:
            point_time = datetime.datetime.fromisoformat(ts)
            if point_time.tzinfo is None:
                point_time = point_time.replace(tzinfo=datetime.timezone.utc)
        else:
            point_time = datetime.datetime.now(datetime.timezone.utc)
    except Exception:
        point_time = datetime.datetime.now(datetime.timezone.utc)

    # previous location
    prev_locations = ride.locations or []
    dist_km = 0.0
    instant_speed_kmh = 0.0

    if prev_locations:
        last = prev_locations[-1]
        last_lat = float(last.get("lat"))
        last_lon = float(last.get("lon"))
        last_ts = None
        try:
            last_ts = datetime.datetime.fromisoformat(last.get("ts")) if last.get("ts") else None
            if last_ts and last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=datetime.timezone.utc)
        except Exception:
            last_ts = None

        # compute distance
        dist_km = haversine_km(last_lat, last_lon, float(lat), float(lon))

        # Ignore small GPS drift
        if dist_km < MIN_MOVEMENT_KM:
            dist_km = 0.0

        # compute time delta in seconds
        if last_ts:
            delta_s = (point_time - last_ts).total_seconds()
            if delta_s > 0:
                delta_h = delta_s / 3600.0
                instant_speed_kmh = dist_km / delta_h if delta_h > 0 else 0.0

                # Ignore unrealistic speeds
                if instant_speed_kmh > MAX_REALISTIC_SPEED:
                    instant_speed_kmh = 0.0
                    dist_km = 0.0

                # Ignore very slow speeds
                if instant_speed_kmh < MIN_SPEED_THRESHOLD:
                    instant_speed_kmh = 0.0
                    dist_km = 0.0
            else:
                instant_speed_kmh = 0.0
        else:
            instant_speed_kmh = 0.0

    # append new location
    new_point = {"lat": float(lat), "lon": float(lon), "ts": point_time.isoformat()}
    prev_locations.append(new_point)
    ride.locations = prev_locations

    # update distance
    ride.distance = float((ride.distance or 0.0) + dist_km)

    # compute avg_speed based on total distance and elapsed time
    # compute avg_speed based on total distance and elapsed time
        # compute avg_speed based on total distance and elapsed time
    try:
        start_time = ride.start_time

        if start_time.tzinfo is None:
            start_time = start_time.replace(
                tzinfo=datetime.timezone.utc
            )

        elapsed_seconds = (point_time - start_time).total_seconds()

        if elapsed_seconds > 0:
            total_hours = elapsed_seconds / 3600.0
            ride.avg_speed = ride.distance / total_hours
        else:
            ride.avg_speed = 0.0

    except Exception:
        ride.avg_speed = 0.0

    # --------------------------
    # Fuel calculations
    # --------------------------
            # --------------------------
    # Fuel calculations
    # --------------------------
    vehicle = db.query(Vehicle).filter(
        Vehicle.id == ride.vehicle_id
    ).first()

    if vehicle and vehicle.mileage and vehicle.mileage > 0:
        fuel_used_now = dist_km / float(vehicle.mileage)

        ride.fuel_used = float((ride.fuel_used or 0.0) + fuel_used_now)
        ride.fuel_remaining = max(
            0.0,
            float(ride.start_fuel) - float(ride.fuel_used)
        )

    # Save everything
    db.commit()
    db.refresh(ride)

    return {
        "distance_km": round(ride.distance or 0.0, 4),
        "avg_speed_kmh": round(ride.avg_speed or 0.0, 2),
        "fuel_used_l": round(ride.fuel_used or 0.0, 4),
        "fuel_left_l": round(ride.fuel_remaining or 0.0, 4),
        "last_location": ride.locations[-1] if ride.locations else None
    }


# --------------------------
# End Ride (finalize + summary)
# --------------------------
@router.post("/end")
def end_ride(data: dict, db: Session = Depends(get_db)):
    """
    Expects: { ride_id }
    Finalizes ride and returns summary.
    """
    ride_id = data.get("ride_id")
    if not ride_id:
        raise HTTPException(status_code=400, detail="ride_id required")

    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    ride.end_time = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    db.refresh(ride)

    # compute duration (seconds)
    duration_s = None
    try:
        if ride.start_time and ride.end_time:
            duration_s = (ride.end_time - ride.start_time).total_seconds()
    except Exception:
        duration_s = None

    # Minimum ride validation rule
    MIN_RIDE_DURATION = 10
    MIN_RIDE_DISTANCE = 0.05

    if duration_s is not None:
        if duration_s < MIN_RIDE_DURATION and (ride.distance or 0.0) < MIN_RIDE_DISTANCE:
            ride.distance = 0.0
            ride.fuel_used = 0.0
            ride.fuel_remaining = ride.start_fuel
            ride.avg_speed = 0.0
            db.commit()

    # final calculations
    vehicle = db.query(Vehicle).filter(Vehicle.id == ride.vehicle_id).first()
    mileage = float(vehicle.mileage) if vehicle and vehicle.mileage else None

    fuel_used = float(ride.fuel_used or 0.0)
    fuel_left = float(ride.fuel_remaining or 0.0)
    distance = float(ride.distance or 0.0)
    avg_speed = float(ride.avg_speed or 0.0)

    # --------------------------
    # Predictive Range Calculation
    # --------------------------
    user_rides = db.query(Ride).filter(
        Ride.user_id == ride.user_id,
        Ride.fuel_used > 0,
        Ride.distance > 0,
        Ride.id != ride.id
    ).all()

    total_distance = 0.0
    total_fuel = 0.0

    for r in user_rides:
        total_distance += float(r.distance or 0.0)
        total_fuel += float(r.fuel_used or 0.0)

    if total_fuel > 0:
        user_avg_mileage = total_distance / total_fuel
    else:
        user_avg_mileage = mileage

    predicted_range_km = None
    if user_avg_mileage and fuel_left:
        predicted_range_km = round(fuel_left * user_avg_mileage, 2)

    # Low fuel alert logic
    LOW_RANGE_THRESHOLD = 15
    low_fuel_alert = False

    if predicted_range_km is not None:
        if predicted_range_km <= LOW_RANGE_THRESHOLD:
            low_fuel_alert = True

    # computed mileage (distance per litre)
    computed_mileage = round(distance / fuel_used, 2) if fuel_used and fuel_used > 0 else None

    # duration string
    duration_str = None
    if duration_s is not None:
        hrs = int(duration_s // 3600)
        mins = int((duration_s % 3600) // 60)
        secs = int(duration_s % 60)
        duration_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

    return {
        "message": "Ride ended",
        "ride_id": ride.id,
        "distance_km": round(distance, 4),
        "fuel_used_l": round(fuel_used, 4),
        "fuel_left_l": round(fuel_left, 4),
        "mileage_km_per_l": computed_mileage,
        "avg_speed_kmh": round(avg_speed, 2),
        "duration": duration_str,
        "predicted_range_km": predicted_range_km,
        "low_fuel_alert": low_fuel_alert,
        "last_location": ride.locations[-1] if ride.locations else None,
    }

# --------------------------
# Nearest Petrol Pumps (OpenStreetMap Overpass API)
# --------------------------
@router.get("/nearby_fuel")
def nearby_fuel(lat: float, lon: float):
    """
    Returns nearest petrol pumps using OpenStreetMap.
    """
    try:
        overpass_url = "https://overpass-api.de/api/interpreter"

        query = f"""
        [out:json];
        node
          ["amenity"="fuel"]
          (around:5000,{lat},{lon});
        out;
        """

        response = requests.post(overpass_url, data=query, timeout=10)
        data = response.json()

        stations = []
        for element in data.get("elements", [])[:5]:  # top 5 only
            stations.append({
                "name": element.get("tags", {}).get("name", "Fuel Station"),
                "lat": element.get("lat"),
                "lon": element.get("lon")
            })

        return {"stations": stations}

    except Exception as e:
        return {"stations": [], "error": str(e)}



# --------------------------
# Recent rides for user
# --------------------------
@router.get("/recent/{user_id}")
def recent_rides(user_id: int, limit: int = 10, db: Session = Depends(get_db)):

    rides = (
        db.query(Ride)
        .filter(Ride.user_id == user_id)
        .order_by(Ride.start_time.desc())
        .limit(limit)
        .all()
    )

    result = []

    for r in rides:

        duration = "--"

        if r.start_time and r.end_time:
            total_seconds = int((r.end_time - r.start_time).total_seconds())

            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            duration = f"{hours:02}:{minutes:02}:{seconds:02}"

        result.append({
            "ride_id": r.id,
            "vehicle_id": r.vehicle_id,
            "start_time": r.start_time.isoformat() if r.start_time else None,
            "end_time": r.end_time.isoformat() if r.end_time else None,
            "distance_km": r.distance,
            "fuel_used_l": r.fuel_used,
            "fuel_left_l": r.fuel_remaining,
            "avg_speed_kmh": r.avg_speed,
            "duration": duration
        })

    return {"rides": result}