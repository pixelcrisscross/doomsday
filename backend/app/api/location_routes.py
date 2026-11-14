from typing import List, Dict, Any
from fastapi import APIRouter, Query, HTTPException

from backend.app.services.location_service import location_service
from backend.app.schemas.schemas import DamageMapPoint, HeatmapPoint, CityPotholeSummary

router = APIRouter(prefix="/location", tags=["Location & Damage Map"])

@router.get("/damage-points", response_model=List[DamageMapPoint])
def get_damage_map_points():
    """Retrieves all georeferenced road distress locations for the interactive map."""
    return location_service.get_damage_points()

@router.get("/heatmap", response_model=List[HeatmapPoint])
def get_pothole_heatmap():
    """Retrieves weighted coordinates for urban pothole density heatmap rendering."""
    return location_service.get_heatmap_points()

@router.get("/city-stats", response_model=CityPotholeSummary)
def get_city_pothole_statistics(city: str = Query("Bengaluru Urban")):
    """Retrieves real-time totals of potholes across the city, active hazards, and repair rate."""
    return location_service.get_city_summary(city)

@router.get("/geofences")
def get_geofences():
    """Retrieves 25m duplicate proximity geofence radius coordinates."""
    return location_service.get_geofences()

@router.get("/reverse-geocode")
def reverse_geocode(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0)
):
    """Converts latitude and longitude into a reverse-geocoded road address."""
    addr = location_service.reverse_geocode(latitude, longitude)
    return {"latitude": latitude, "longitude": longitude, "address": addr}
