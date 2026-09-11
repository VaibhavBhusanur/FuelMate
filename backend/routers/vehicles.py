import csv
import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Vehicle

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/add")
def add_vehicle(vehicle: dict, db: Session = Depends(get_db)):
    new_vehicle = Vehicle(
        brand=vehicle.get("brand"),
        model=vehicle.get("model"),
        year=vehicle.get("year"),
        mileage=vehicle.get("mileage"),
        tank_capacity=vehicle.get("tank_capacity"),
        owner_id=vehicle.get("owner_id")
    )

    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)

    return {
        "message": "Vehicle added successfully",
        "vehicle": new_vehicle.model
    }


@router.get("/list")
def list_vehicles(db: Session = Depends(get_db)):
    vehicles = db.query(Vehicle).all()

    return {
        "vehicles": [
            {
                "id": v.id,
                "brand": v.brand,
                "model": v.model,
                "year": v.year,
                "mileage": v.mileage,
                "tank_capacity": v.tank_capacity
            }
            for v in vehicles
        ]
    }


@router.get("/{vehicle_id}")
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()

    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    return {
        "id": v.id,
        "brand": v.brand,
        "model": v.model,
        "year": v.year,
        "mileage": v.mileage,
        "tank_capacity": v.tank_capacity,
        "owner_id": v.owner_id
    }


@router.post("/import_csv")
def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import multiple vehicles from a CSV file."""

    try:
        contents = file.file.read().decode("utf-8").splitlines()
        reader = csv.DictReader(contents)

        added_count = 0

        for row in reader:

            mileage_str = (row.get("mileage") or "0").strip()
            tank_str = (row.get("tank_capacity") or "0").strip()

            mileage_match = re.search(r"\d+(\.\d+)?", mileage_str)
            tank_match = re.search(r"\d+(\.\d+)?", tank_str)

            mileage = float(mileage_match.group()) if mileage_match else 0.0
            tank_capacity = float(tank_match.group()) if tank_match else 0.0

            year = None
            if row.get("year"):
                try:
                    year = int(row.get("year"))
                except ValueError:
                    year = None

            owner_id = 1
            if row.get("owner_id"):
                try:
                    owner_id = int(row.get("owner_id"))
                except ValueError:
                    owner_id = 1

            vehicle = Vehicle(
                brand=row.get("brand"),
                model=row.get("model"),
                year=year,
                mileage=mileage,
                tank_capacity=tank_capacity,
                owner_id=owner_id
            )

            db.add(vehicle)
            added_count += 1

        db.commit()

        return {
            "message": f"{added_count} vehicles imported successfully"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))