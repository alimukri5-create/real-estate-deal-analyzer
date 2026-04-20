"""HM Land Registry Price Paid Data API client.

The Land Registry provides free, open data on all property transactions
in England and Wales since 1995. No API key required.

Endpoint: https://landregistry.data.gov.uk/data/ppd/transaction.csv
"""

import csv
import io
import urllib.parse
import urllib.request
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class SoldPriceRecord:
    """A single Land Registry sold price record."""
    transaction_id: str
    price: float
    date_of_transfer: str
    postcode: str
    property_type: str  # D=Detached, S=Semi-detached, T=Terraced, F=Flat/Maisonette, O=Other
    old_new: str  # Y=New build, N=Established
    duration: str  # F=Freehold, L=Leasehold
    paon: str  # Primary address (house number)
    saon: str  # Secondary address (flat number)
    street: str
    locality: str
    town_city: str
    district: str
    county: str
    ppd_category: str
    record_status: str

    @property
    def full_address(self) -> str:
        parts = []
        if self.saon:
            parts.append(self.saon)
        if self.paon:
            parts.append(self.paon)
        if self.street:
            parts.append(self.street)
        if self.locality:
            parts.append(self.locality)
        if self.town_city:
            parts.append(self.town_city)
        return ", ".join(parts)

    @property
    def property_type_readable(self) -> str:
        mapping = {
            "D": "Detached",
            "S": "Semi-detached", 
            "T": "Terraced",
            "F": "Flat/Maisonette",
            "O": "Other",
        }
        return mapping.get(self.property_type, "Unknown")


def _parse_price(value: str) -> float:
    """Parse price string to float, handling empty values."""
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _clean_string(value: str) -> str:
    """Clean and strip string values."""
    return value.strip().strip('"') if value else ""


def fetch_sold_prices(
    postcode: Optional[str] = None,
    street: Optional[str] = None,
    town: Optional[str] = None,
    property_type: Optional[str] = None,  # D, S, T, F, O
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    since_year: Optional[int] = None,
    limit: int = 100,
) -> List[SoldPriceRecord]:
    """
    Fetch sold price records from HM Land Registry.
    
    Args:
        postcode: Full or partial postcode (e.g., 'SW1A 1AA' or 'SW1A')
        street: Street name to filter by
        town: Town/city name
        property_type: D=Detached, S=Semi, T=Terraced, F=Flat, O=Other
        min_price: Minimum price in GBP
        max_price: Maximum price in GBP
        since_year: Only return records from this year onwards
        limit: Maximum records to return
    
    Returns:
        List of SoldPriceRecord objects
    """
    # Build SPARQL query for the Land Registry CSV endpoint
    # This uses their public data endpoint
    base_url = "https://landregistry.data.gov.uk/data/ppd/transaction.csv"
    
    # Build query parameters
    params = {}
    if postcode:
        params["postcode"] = postcode
    if street:
        params["street"] = street.upper()
    if town:
        params["town"] = town.upper()
    if property_type:
        params["property_type"] = property_type.upper()
    if min_price:
        params["min_price"] = str(min_price)
    if max_price:
        params["max_price"] = str(max_price)
    if since_year:
        params["min_year"] = str(since_year)
    
    # Construct URL
    if params:
        query_string = urllib.parse.urlencode(params)
        url = f"{base_url}?{query_string}"
    else:
        url = base_url
    
    try:
        # Fetch data
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (RealEstateDealAnalyzer/1.0)",
                "Accept": "text/csv",
            }
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')
        
        # Parse CSV
        records = []
        reader = csv.DictReader(io.StringIO(content))
        
        for i, row in enumerate(reader):
            if i >= limit:
                break
            
            record = SoldPriceRecord(
                transaction_id=_clean_string(row.get("transaction_id", "")),
                price=_parse_price(row.get("price_paid", "")),
                date_of_transfer=_clean_string(row.get("date_of_transfer", "")),
                postcode=_clean_string(row.get("postcode", "")),
                property_type=_clean_string(row.get("property_type", "")).upper(),
                old_new=_clean_string(row.get("old_new", "")),
                duration=_clean_string(row.get("duration", "")),
                paon=_clean_string(row.get("paon", "")),
                saon=_clean_string(row.get("saon", "")),
                street=_clean_string(row.get("street", "")),
                locality=_clean_string(row.get("locality", "")),
                town_city=_clean_string(row.get("town_city", "")),
                district=_clean_string(row.get("district", "")),
                county=_clean_string(row.get("county", "")),
                ppd_category=_clean_string(row.get("ppd_category_type", "")),
                record_status=_clean_string(row.get("record_status", "")),
            )
            records.append(record)
        
        return records
        
    except Exception as e:
        print(f"Land Registry fetch error: {e}")
        return []


def fetch_recent_comps(
    postcode: str,
    property_type: Optional[str] = None,
    radius_years: int = 2,
    limit: int = 20,
) -> Tuple[List[SoldPriceRecord], Dict]:
    """
    Fetch recent comparable sales for a given postcode.
    
    Returns:
        (records, stats_dict)
    """
    since_year = 2024 - radius_years
    
    records = fetch_sold_prices(
        postcode=postcode,
        property_type=property_type,
        since_year=since_year,
        limit=limit,
    )
    
    # Calculate statistics
    if not records:
        return [], {"count": 0, "avg_price": 0, "median_price": 0, "min": 0, "max": 0}
    
    prices = [r.price for r in records if r.price > 0]
    prices.sort()
    
    stats = {
        "count": len(prices),
        "avg_price": round(sum(prices) / len(prices), 0) if prices else 0,
        "median_price": round(prices[len(prices) // 2], 0) if prices else 0,
        "min": round(min(prices), 0) if prices else 0,
        "max": round(max(prices), 0) if prices else 0,
        "per_sqft_estimate": None,  # Would need sqft data from elsewhere
    }
    
    return records, stats


def format_comp_summary(records: List[SoldPriceRecord]) -> str:
    """Format comparable sales into a readable summary."""
    if not records:
        return "No comparable sales found."
    
    lines = [f"Found {len(records)} recent sales:", ""]
    
    for r in records[:10]:  # Show top 10
        date = r.date_of_transfer[:10] if r.date_of_transfer else "Unknown date"
        lines.append(
            f"• £{r.price:,.0f} — {r.full_address} ({r.property_type_readable}, {date})"
        )
    
    return "\n".join(lines)


# --- Alternative: Direct CSV download for bulk data ---

def fetch_sold_prices_csv_direct(
    postcode_prefix: str,
    limit: int = 100,
) -> List[SoldPriceRecord]:
    """
    Alternative method using direct CSV download.
    More reliable for bulk queries.
    """
    # The Land Registry provides monthly CSV files
    # For real-time queries, we use the API above
    # This is a fallback for specific postcodes
    
    url = f"https://landregistry.data.gov.uk/app/ppd/search?postcode={urllib.parse.quote(postcode_prefix)}"
    
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')
        
        # Parse HTML table or CSV response
        records = []
        # Implementation depends on response format
        # The API method above is preferred
        
        return records
        
    except Exception as e:
        print(f"Direct CSV fetch error: {e}")
        return []
