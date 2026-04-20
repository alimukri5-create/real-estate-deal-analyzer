"""Live data fetcher - combines Land Registry sold prices and Rightmove rentals.

This is the main interface for pulling real market data into the deal analyzer.
"""

from typing import Dict, List, Optional, Tuple
import land_registry
import rightmove_scraper


def fetch_live_comps(
    postcode: str,
    bedrooms: Optional[int] = None,
    property_type: Optional[str] = None,
    radius_miles: float = 0.5,
) -> Dict:
    """
    Fetch live comparable data for a property.
    
    Returns combined data from:
    - Land Registry: Recent sold prices
    - Rightmove: Active rental listings (for yield calc)
    
    Args:
        postcode: UK postcode
        bedrooms: Number of bedrooms for rental comp filtering
        property_type: 'D', 'S', 'T', 'F' for Land Registry filter
        radius_miles: Search radius for Rightmove
    
    Returns:
        Dict with keys:
        - sold_prices: List of recent sold prices
        - sold_stats: Summary stats (avg, median, count)
        - rental_comps: List of active rental listings
        - rental_stats: Summary stats (avg rent, yield estimate)
        - estimated_yield: Gross yield based on avg price / avg rent
    """
    result = {
        "postcode": postcode,
        "sold_prices": [],
        "sold_stats": {},
        "rental_comps": [],
        "rental_stats": {},
        "estimated_yield": None,
        "price_per_sqft": None,
    }
    
    # 1. Fetch Land Registry sold prices
    sold_records, sold_stats = land_registry.fetch_recent_comps(
        postcode=postcode,
        property_type=property_type,
        radius_years=2,
        limit=50,
    )
    
    result["sold_prices"] = [
        {
            "price": r.price,
            "date": r.date_of_transfer,
            "address": r.full_address,
            "type": r.property_type_readable,
        }
        for r in sold_records[:20]
    ]
    result["sold_stats"] = sold_stats
    
    # 2. Fetch Rightmove rental comps
    if bedrooms:
        rental_listings, rental_stats = rightmove_scraper.get_rental_comps(
            postcode=postcode,
            bedrooms=bedrooms,
            radius_miles=radius_miles,
        )
        
        result["rental_comps"] = [
            {
                "rent": l.monthly_rent,
                "address": l.address,
                "bedrooms": l.bedrooms,
                "type": l.property_type,
                "sqft": l.sqft,
                "url": l.listing_url,
            }
            for l in rental_listings[:15]
        ]
        result["rental_stats"] = rental_stats
        
        # 3. Calculate estimated yield
        if sold_stats.get("avg_price", 0) > 0 and rental_stats.get("avg_annual_rent", 0) > 0:
            gross_yield = rental_stats["avg_annual_rent"] / sold_stats["avg_price"]
            result["estimated_yield"] = round(gross_yield, 4)
    
    # 4. Calculate £/sqft from sold prices if we had sqft data
    # (We don't get sqft from Land Registry, but we can estimate from rental listings)
    if result["rental_comps"]:
        sqft_values = [c["sqft"] for c in result["rental_comps"] if c.get("sqft")]
        if sqft_values and sold_stats.get("avg_price"):
            avg_sqft = sum(sqft_values) / len(sqft_values)
            result["price_per_sqft"] = round(sold_stats["avg_price"] / avg_sqft, 2)
    
    return result


def format_live_comps_report(data: Dict) -> str:
    """Format live comp data into a readable report."""
    lines = [f"📊 Live Market Data for {data['postcode']}", ""]
    
    # Sold prices
    sold_stats = data.get("sold_stats", {})
    if sold_stats.get("count", 0) > 0:
        lines.extend([
            f"🏠 Sold Prices (last 2 years):",
            f"   {sold_stats['count']} sales | Avg: £{sold_stats['avg_price']:,.0f} | Median: £{sold_stats['median_price']:,.0f}",
            f"   Range: £{sold_stats['min']:,.0f} - £{sold_stats['max']:,.0f}",
            "",
        ])
    else:
        lines.extend([
            "🏠 Sold Prices: No recent sales found",
            "",
        ])
    
    # Rental comps
    rental_stats = data.get("rental_stats", {})
    if rental_stats.get("returned", 0) > 0:
        lines.extend([
            f"🏘️ Rental Comps (active listings):",
            f"   {rental_stats['returned']} properties | Avg: £{rental_stats['avg_monthly_rent']:,.0f}/mo",
            f"   Range: £{rental_stats['min_rent']:,.0f} - £{rental_stats['max_rent']:,.0f}/mo",
            "",
        ])
    else:
        lines.extend([
            "🏘️ Rental Comps: No active rentals found",
            "",
        ])
    
    # Yield estimate
    if data.get("estimated_yield"):
        yield_pct = data["estimated_yield"] * 100
        lines.append(f"📈 Estimated Gross Yield: {yield_pct:.2f}%")
    
    if data.get("price_per_sqft"):
        lines.append(f"📐 Est. £/sqft: £{data['price_per_sqft']:,.2f}")
    
    return "\n".join(lines)


def get_fair_value_estimate(
    postcode: str,
    bedrooms: int,
    asking_price: float,
    property_type: Optional[str] = None,
) -> Dict:
    """
    Get a real fair value estimate based on live market data.
    
    Uses multiple methods:
    1. Average of recent sold prices (primary)
    2. Rental yield-based valuation (if rental comps available)
    3. £/sqft method (if sqft data available)
    
    Returns dict with valuation bands and recommendation.
    """
    data = fetch_live_comps(
        postcode=postcode,
        bedrooms=bedrooms,
        property_type=property_type,
        radius_miles=0.5,
    )
    
    valuations = []
    methods_used = []
    
    # Method 1: Recent sold price average
    sold_avg = data.get("sold_stats", {}).get("avg_price", 0)
    if sold_avg > 0:
        valuations.append(sold_avg)
        methods_used.append("Recent sales average")
    
    # Method 2: Yield-based (if we have rental comps)
    if data.get("estimated_yield") and data.get("rental_stats"):
        avg_annual_rent = data["rental_stats"].get("avg_annual_rent", 0)
        if avg_annual_rent > 0:
            # Target 5-6% yield for London
            target_yield = 0.055
            yield_value = avg_annual_rent / target_yield
            valuations.append(yield_value)
            methods_used.append(f"Yield-based (target {target_yield*100:.1f}%)")
    
    # Method 3: £/sqft
    price_per_sqft = data.get("price_per_sqft")
    if price_per_sqft:
        # Estimate sqft from rental comps if available
        sqft_values = [c.get("sqft") for c in data.get("rental_comps", []) if c.get("sqft")]
        if sqft_values:
            avg_sqft = sum(sqft_values) / len(sqft_values)
            sqft_value = avg_sqft * price_per_sqft
            valuations.append(sqft_value)
            methods_used.append("£/sqft method")
    
    # Calculate bands
    if len(valuations) >= 2:
        valuations.sort()
        base_fair = sum(valuations) / len(valuations)
        low_fair = valuations[0] * 0.95  # 5% discount to most conservative
        high_fair = valuations[-1] * 1.05  # 5% premium to most optimistic
    elif len(valuations) == 1:
        base_fair = valuations[0]
        low_fair = base_fair * 0.90
        high_fair = base_fair * 1.10
    else:
        return {
            "error": "Insufficient market data for valuation",
            "data": data,
            "methods_tried": ["Land Registry sold prices", "Rightmove rental comps"],
        }
    
    # Compare to asking price
    margin = (asking_price - base_fair) / base_fair if base_fair else 0
    if margin < -0.05:
        flag = "underpay"
        recommendation = "✅ Potential deal - asking below market"
    elif margin > 0.05:
        flag = "overpay"
        recommendation = f"⚠️ OVERPAY - Asking {margin*100:.1f}% above estimated fair value"
    else:
        flag = "fair"
        recommendation = "✓ Fair price - within market range"
    
    # Max bid recommendation (10% below base fair for margin of safety)
    max_bid = base_fair * 0.90
    
    return {
        "asking_price": asking_price,
        "fair_value_base": round(base_fair, 0),
        "fair_value_low": round(low_fair, 0),
        "fair_value_high": round(high_fair, 0),
        "max_bid": round(max_bid, 0),
        "margin_vs_fair": round(margin * 100, 2),
        "flag": flag,
        "recommendation": recommendation,
        "methods_used": methods_used,
        "live_data": data,
    }
