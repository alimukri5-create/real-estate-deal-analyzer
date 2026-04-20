"""Rightmove rental and sales listing scraper.

Rightmove doesn't have a public consumer API, but their internal
backend endpoints are accessible for scraping rental comparables.

This module fetches live rental listings for comp analysis.
"""

import json
import urllib.parse
import urllib.request
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RentalListing:
    """A single rental listing from Rightmove."""
    id: str
    address: str
    monthly_rent: float
    bedrooms: int
    bathrooms: int
    property_type: str  # e.g., "Flat", "House", "Terraced"
    postcode: str
    latitude: float
    longitude: float
    listing_url: str
    agent_name: str
    date_added: str
    description: str
    sqft: Optional[float] = None

    @property
    def annual_rent(self) -> float:
        return self.monthly_rent * 12

    @property
    def rent_per_sqft_annual(self) -> Optional[float]:
        if self.sqft and self.sqft > 0:
            return self.annual_rent / self.sqft
        return None


@dataclass
class SalesListing:
    """A single sales listing from Rightmove (for price comps)."""
    id: str
    address: str
    price: float
    bedrooms: int
    bathrooms: int
    property_type: str
    postcode: str
    latitude: float
    longitude: float
    listing_url: str
    agent_name: str
    date_added: str
    description: str
    sqft: Optional[float] = None


# Rightmove internal API endpoints
RIGHTMOVE_RENTAL_API = "https://www.rightmove.co.uk/api/property/search"
RIGHTMOVE_SALES_API = "https://www.rightmove.co.uk/api/property/search"

# Location identifier mapping (would need to be built or fetched)
# For now we use postcode search via their search API


def _make_request(url: str, headers: Optional[Dict] = None) -> Dict:
    """Make HTTP request and return JSON response."""
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-GB,en;q=0.9",
        "Referer": "https://www.rightmove.co.uk/",
    }
    if headers:
        default_headers.update(headers)
    
    req = urllib.request.Request(url, headers=default_headers)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Rightmove API error: {e}")
        return {}


def search_rental_listings(
    postcode: str,
    radius_miles: float = 0.25,
    min_bedrooms: Optional[int] = None,
    max_bedrooms: Optional[int] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    property_types: Optional[List[str]] = None,
    max_results: int = 24,
) -> Tuple[List[RentalListing], Dict]:
    """
    Search Rightmove for rental listings near a postcode.
    
    Args:
        postcode: UK postcode (e.g., 'SW1A 1AA')
        radius_miles: Search radius (0.25 = quarter mile, good for same street)
        min_bedrooms: Minimum bedrooms
        max_bedrooms: Maximum bedrooms
        min_price: Minimum monthly rent
        max_price: Maximum monthly rent
        property_types: e.g., ['flat', 'house', 'bungalow']
        max_results: Max listings to return
    
    Returns:
        (listings, metadata_dict)
    """
    # Rightmove uses location identifiers; we need to resolve postcode first
    # For simplicity, we'll use their search API with location identifier
    
    # Step 1: Resolve postcode to location identifier
    location_id = _resolve_postcode(postcode)
    if not location_id:
        return [], {"error": f"Could not resolve postcode: {postcode}"}
    
    # Step 2: Build search URL
    params = {
        "locationIdentifier": location_id,
        "radius": str(radius_miles),
        "index": "0",
        "numberOfProperties": str(max_results),
        "sortType": "6",  # Recently added first
        "viewType": "LIST",
        "channel": "RENT",  # Rental channel
        "areaSizeUnit": "sqft",
        "currencyCode": "GBP",
        "isFetching": "false",
        "viewport": "",
    }
    
    if min_bedrooms is not None:
        params["minBedrooms"] = str(min_bedrooms)
    if max_bedrooms is not None:
        params["maxBedrooms"] = str(max_bedrooms)
    if min_price is not None:
        params["minPrice"] = str(min_price)
    if max_price is not None:
        params["maxPrice"] = str(max_price)
    
    query_string = urllib.parse.urlencode(params)
    url = f"{RIGHTMOVE_RENTAL_API}?{query_string}"
    
    # Fetch data
    data = _make_request(url)
    
    if not data or "properties" not in data:
        return [], {"error": "No properties found or API error"}
    
    listings = []
    for prop in data.get("properties", []):
        listing = _parse_rental_property(prop)
        if listing:
            listings.append(listing)
    
    metadata = {
        "total_results": data.get("resultCount", 0),
        "returned": len(listings),
        "postcode": postcode,
        "radius_miles": radius_miles,
    }
    
    return listings, metadata


def search_sales_listings(
    postcode: str,
    radius_miles: float = 0.25,
    min_bedrooms: Optional[int] = None,
    max_bedrooms: Optional[int] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    max_results: int = 24,
) -> Tuple[List[SalesListing], Dict]:
    """Search Rightmove for sales listings (active properties on market)."""
    location_id = _resolve_postcode(postcode)
    if not location_id:
        return [], {"error": f"Could not resolve postcode: {postcode}"}
    
    params = {
        "locationIdentifier": location_id,
        "radius": str(radius_miles),
        "index": "0",
        "numberOfProperties": str(max_results),
        "sortType": "6",
        "viewType": "LIST",
        "channel": "BUY",  # Sales channel
        "areaSizeUnit": "sqft",
        "currencyCode": "GBP",
        "isFetching": "false",
    }
    
    if min_bedrooms is not None:
        params["minBedrooms"] = str(min_bedrooms)
    if max_bedrooms is not None:
        params["maxBedrooms"] = str(max_bedrooms)
    if min_price is not None:
        params["minPrice"] = str(min_price)
    if max_price is not None:
        params["maxPrice"] = str(max_price)
    
    query_string = urllib.parse.urlencode(params)
    url = f"{RIGHTMOVE_SALES_API}?{query_string}"
    
    data = _make_request(url)
    
    if not data or "properties" not in data:
        return [], {"error": "No properties found or API error"}
    
    listings = []
    for prop in data.get("properties", []):
        listing = _parse_sales_property(prop)
        if listing:
            listings.append(listing)
    
    metadata = {
        "total_results": data.get("resultCount", 0),
        "returned": len(listings),
        "postcode": postcode,
        "radius_miles": radius_miles,
    }
    
    return listings, metadata


def _resolve_postcode(postcode: str) -> Optional[str]:
    """
    Resolve a UK postcode to a Rightmove location identifier.
    
    Rightmove uses location identifiers like 'POSTCODE^1234567'
    We fetch this from their typeahead API.
    """
    # Clean postcode
    clean_pc = postcode.strip().upper().replace(" ", "")
    
    # Try to fetch from Rightmove's location API
    url = f"https://www.rightmove.co.uk/typeAhead/uknostreet/{urllib.parse.quote(clean_pc)}"
    
    try:
        data = _make_request(url)
        
        # Parse response to find matching location
        if "typeAheadLocations" in data:
            for loc in data["typeAheadLocations"]:
                if loc.get("locationIdentifier", "").startswith("POSTCODE"):
                    return loc["locationIdentifier"]
        
        # Fallback: try alternative endpoint
        alt_url = f"https://www.rightmove.co.uk/typeAhead/uk/{urllib.parse.quote(clean_pc)}"
        alt_data = _make_request(alt_url)
        
        if "typeAheadLocations" in alt_data:
            for loc in alt_data["typeAheadLocations"]:
                if "POSTCODE" in loc.get("locationIdentifier", ""):
                    return loc["locationIdentifier"]
        
        return None
        
    except Exception as e:
        print(f"Postcode resolution error: {e}")
        return None


def _parse_rental_property(prop: Dict) -> Optional[RentalListing]:
    """Parse a Rightmove property dict into RentalListing."""
    try:
        # Extract price
        price_display = prop.get("price", {}).get("amount", "0")
        monthly_rent = float(price_display) if price_display else 0
        
        # Extract address components
        address = prop.get("displayAddress", "")
        
        # Extract bedrooms/bathrooms
        bedrooms = 0
        bathrooms = 0
        for room in prop.get("rooms", []):
            if room.get("type") == "BEDROOM":
                bedrooms = room.get("value", 0)
            elif room.get("type") == "BATHROOM":
                bathrooms = room.get("value", 0)
        
        # Property type
        property_type = prop.get("propertySubType", prop.get("propertyType", ""))
        
        # Location
        location = prop.get("location", {})
        postcode = location.get("postcode", "")
        lat = location.get("latitude", 0)
        lon = location.get("longitude", 0)
        
        # Sqft (if available)
        sqft = None
        if "floorArea" in prop and prop["floorArea"]:
            sqft = prop["floorArea"].get("maxFloorArea", {}).get("value")
            if sqft:
                # Convert sqm to sqft if needed
                unit = prop["floorArea"].get("maxFloorArea", {}).get("unit", "sqft")
                if unit.lower() == "sqm":
                    sqft = sqft * 10.764
        
        listing = RentalListing(
            id=str(prop.get("id", "")),
            address=address,
            monthly_rent=monthly_rent,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            property_type=property_type,
            postcode=postcode,
            latitude=lat,
            longitude=lon,
            listing_url=f"https://www.rightmove.co.uk/properties/{prop.get('id', '')}",
            agent_name=prop.get("customer", {}).get("brandTradingName", ""),
            date_added=prop.get("added", ""),
            description=prop.get("summary", ""),
            sqft=sqft,
        )
        
        return listing
        
    except Exception as e:
        print(f"Parse error: {e}")
        return None


def _parse_sales_property(prop: Dict) -> Optional[SalesListing]:
    """Parse a Rightmove property dict into SalesListing."""
    try:
        price_display = prop.get("price", {}).get("amount", "0")
        price = float(price_display) if price_display else 0
        
        address = prop.get("displayAddress", "")
        
        bedrooms = 0
        bathrooms = 0
        for room in prop.get("rooms", []):
            if room.get("type") == "BEDROOM":
                bedrooms = room.get("value", 0)
            elif room.get("type") == "BATHROOM":
                bathrooms = room.get("value", 0)
        
        property_type = prop.get("propertySubType", prop.get("propertyType", ""))
        
        location = prop.get("location", {})
        postcode = location.get("postcode", "")
        lat = location.get("latitude", 0)
        lon = location.get("longitude", 0)
        
        sqft = None
        if "floorArea" in prop and prop["floorArea"]:
            sqft = prop["floorArea"].get("maxFloorArea", {}).get("value")
            if sqft:
                unit = prop["floorArea"].get("maxFloorArea", {}).get("unit", "sqft")
                if unit.lower() == "sqm":
                    sqft = sqft * 10.764
        
        listing = SalesListing(
            id=str(prop.get("id", "")),
            address=address,
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            property_type=property_type,
            postcode=postcode,
            latitude=lat,
            longitude=lon,
            listing_url=f"https://www.rightmove.co.uk/properties/{prop.get('id', '')}",
            agent_name=prop.get("customer", {}).get("brandTradingName", ""),
            date_added=prop.get("added", ""),
            description=prop.get("summary", ""),
            sqft=sqft,
        )
        
        return listing
        
    except Exception as e:
        print(f"Parse error: {e}")
        return None


# --- Convenience functions for deal analysis ---

def get_rental_comps(
    postcode: str,
    bedrooms: int,
    radius_miles: float = 0.5,
) -> Tuple[List[RentalListing], Dict]:
    """
    Get rental comparables for a specific property type near a postcode.
    
    Returns listings and summary stats (avg rent, median rent, etc.)
    """
    listings, meta = search_rental_listings(
        postcode=postcode,
        radius_miles=radius_miles,
        min_bedrooms=bedrooms,
        max_bedrooms=bedrooms,
        max_results=50,
    )
    
    if not listings:
        return [], meta
    
    rents = [l.monthly_rent for l in listings if l.monthly_rent > 0]
    rents.sort()
    
    stats = {
        **meta,
        "avg_monthly_rent": round(sum(rents) / len(rents), 0) if rents else 0,
        "median_monthly_rent": round(rents[len(rents) // 2], 0) if rents else 0,
        "min_rent": round(min(rents), 0) if rents else 0,
        "max_rent": round(max(rents), 0) if rents else 0,
        "avg_annual_rent": round(sum(rents) / len(rents) * 12, 0) if rents else 0,
    }
    
    return listings, stats


def format_rental_comps(listings: List[RentalListing], stats: Dict) -> str:
    """Format rental comparables for display."""
    lines = [
        f"Rental Comps ({stats.get('returned', 0)} properties within {stats.get('radius_miles', 0.5)} miles)",
        "",
        f"Average Rent: £{stats.get('avg_monthly_rent', 0):,.0f}/month (£{stats.get('avg_annual_rent', 0):,.0f}/year)",
        f"Median Rent: £{stats.get('median_monthly_rent', 0):,.0f}/month",
        f"Range: £{stats.get('min_rent', 0):,.0f} - £{stats.get('max_rent', 0):,.0f}/month",
        "",
        "Comparable Properties:",
    ]
    
    for l in listings[:10]:
        sqft_str = f" | {l.sqft:.0f} sqft" if l.sqft else ""
        lines.append(
            f"• £{l.monthly_rent:,.0f}/mo — {l.address} ({l.bedrooms}bed/{l.bathrooms}bath{sqft_str})"
        )
    
    return "\n".join(lines)
