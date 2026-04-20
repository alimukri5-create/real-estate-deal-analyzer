"""Streamlit app — Real Estate Deal Analyzer v1."""
import sys
import streamlit as st
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from extract import extract_text_from_pdf, extract_facts
from scenarios import run_analysis, save_analysis
from memo import generate_memo
from utils import slugify
from live_data import fetch_live_comps, format_live_comps_report, get_fair_value_estimate

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Real Estate DD Analyzer",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏠 Real Estate Deal Analyzer")
st.caption("v1.0 — Upload a memo, enter deal details, get a structured memo")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Deal Inputs")

    address = st.text_input("Property Address", placeholder="e.g. Example Street, London")
    price = st.number_input("Asking Price (£)", min_value=0, value=500000, step=10000)
    hold_years = st.slider("Hold Period (years)", 1, 20, 5)
    strategy = st.selectbox(
        "Strategy",
        [
            ("btl_yield", "Buy-to-Let Yield Play"),
            ("refurb_flip", "Refurb & Flip"),
            ("development", "Development / Heavy Value-Add"),
            ("hold_long", "Long-Term Hold"),
        ],
        format_func=lambda x: x[1],
    )[0]

    rent_annual = st.number_input("Annual Rent (£) — optional", min_value=0, value=0, step=1000)
    sqft = st.number_input("Square Footage — optional", min_value=0, value=0, step=50)

    use_live_data = st.checkbox("🔴 Use Live Market Data", value=True, help="Fetch real sold prices from Land Registry + rental comps from Rightmove")

    postcode = st.text_input("Postcode", placeholder="e.g. SW1A 1AA", help="Required for live data lookup")

    uploaded_file = st.file_uploader("Upload Memo PDF", type=["pdf"])

    analyze_clicked = st.button("🔍 Analyze", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
if analyze_clicked and address and price > 0:
    with st.spinner("Analyzing deal..."):
        # --- PDF extraction ---
        extracted_facts = {}
        if uploaded_file is not None:
            try:
                # Save uploaded file temporarily
                raw_dir = Path("data/raw")
                raw_dir.mkdir(parents=True, exist_ok=True)
                temp_pdf = raw_dir / uploaded_file.name
                with open(temp_pdf, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                raw_text = extract_text_from_pdf(temp_pdf)
                extracted_facts = extract_facts(raw_text)
                st.success(f"PDF extracted: {uploaded_file.name}")
            except Exception as e:
                st.error(f"PDF extraction failed: {e}")

        # --- Run analysis ---
        result = run_analysis(
            address=address,
            price=price,
            hold_years=hold_years,
            strategy=strategy,
            rent_annual=rent_annual if rent_annual > 0 else None,
            sqft=sqft if sqft > 0 else None,
            extracted_facts=extracted_facts,
        )

        # --- Live data fetch ---
        live_data = {}
        live_valuation = {}
        if use_live_data and postcode:
            with st.spinner("Fetching live market data..."):
                try:
                    # Extract bedrooms from facts if available, else default to 2
                    bedrooms = extracted_facts.get("bedrooms", 2)
                    if isinstance(bedrooms, list):
                        bedrooms = int(bedrooms[0]) if bedrooms else 2
                    
                    live_data = fetch_live_comps(
                        postcode=postcode.strip().upper(),
                        bedrooms=int(bedrooms) if bedrooms else 2,
                        property_type=None,  # Auto-detect
                        radius_miles=0.5,
                    )
                    
                    live_valuation = get_fair_value_estimate(
                        postcode=postcode.strip().upper(),
                        bedrooms=int(bedrooms) if bedrooms else 2,
                        asking_price=price,
                        property_type=None,
                    )
                    
                    # Override with live valuation if available
                    if "fair_value_base" in live_valuation:
                        result["valuation"]["base_fair_value"] = live_valuation["fair_value_base"]
                        result["valuation"]["low_fair_value"] = live_valuation["fair_value_low"]
                        result["valuation"]["high_fair_value"] = live_valuation["fair_value_high"]
                        result["valuation"]["max_bid"] = live_valuation["max_bid"]
                        result["valuation"]["margin_pct"] = abs(live_valuation["margin_vs_fair"])
                        result["valuation"]["flag"] = live_valuation["flag"]
                        result["live_data"] = live_data
                        result["live_valuation"] = live_valuation
                    
                    st.success("Live market data fetched!")
                except Exception as e:
                    st.warning(f"Live data fetch failed: {e}")

        # --- Generate memo ---
        memo = generate_memo(result)

        # --- Save to deals folder ---
        deal_id = f"deal_{slugify(address)[:20]}_{price:,.0f}"
        deal_dir = save_analysis(result, deal_id, base_path=".")

        # Save memo as markdown
        memo_path = deal_dir / "output.md"
        with open(memo_path, "w") as f:
            f.write(memo)

        # Also save memo text
        st.session_state["last_result"] = result
        st.session_state["last_memo"] = memo
        st.session_state["deal_dir"] = str(deal_dir)

    st.success(f"Deal saved to: `{deal_dir}`")

# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------
if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    memo = st.session_state["last_memo"]

    val = result["valuation"]
    scen = result["scenario"]

    # --- Top metrics ---
    cols = st.columns(4)
    flag = val.get("flag", "unknown")
    flag_colors = {"underpay": "green", "fair": "orange", "overpay": "red"}
    flag_emoji = {"underpay": "🟢", "fair": "🟡", "overpay": "🔴"}

    with cols[0]:
        st.metric("Asking Price", f"£{val['current_price']:,.0f}")
    with cols[1]:
        st.metric("Base Fair Value", f"£{val['base_fair_value']:,.0f}")
    with cols[2]:
        st.metric("Max Bid", f"£{val['max_bid']:,.0f}")
    with cols[3]:
        st.metric(
            "Verdict",
            f"{flag_emoji.get(flag, '⚪')} {flag.upper()}",
            delta=f"{val['margin_pct']:.1f}% vs base",
            delta_color="inverse" if flag == "overpay" else "normal",
        )

    st.divider()

    # --- Tabs ---
    tab_memo, tab_live, tab_facts, tab_valuation, tab_scenario = st.tabs([
        "📝 Memo", "🔴 Live Market Data", "📄 Extracted Facts", "💰 Valuation", "📊 Scenario"
    ])

    with tab_memo:
        st.markdown(memo)
        st.download_button(
            "Download Memo (.md)",
            memo,
            file_name="deal_memo.md",
            mime="text/markdown",
        )

    with tab_live:
        if "live_data" in result:
            live_data = result["live_data"]
            live_val = result.get("live_valuation", {})
            
            st.subheader("📊 Live Market Data")
            
            if live_val.get("recommendation"):
                st.info(live_val["recommendation"])
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**🏠 Recent Sold Prices**")
                sold_stats = live_data.get("sold_stats", {})
                if sold_stats.get("count", 0) > 0:
                    st.write(f"{sold_stats['count']} sales | Avg: £{sold_stats['avg_price']:,.0f}")
                    for sp in live_data.get("sold_prices", [])[:10]:
                        st.write(f"• £{sp['price']:,.0f} — {sp['address']} ({sp['date'][:10]})")
                else:
                    st.warning("No sold price data found")
            
            with col2:
                st.write("**🏘️ Active Rental Comps**")
                rental_stats = live_data.get("rental_stats", {})
                if rental_stats.get("returned", 0) > 0:
                    st.write(f"{rental_stats['returned']} listings | Avg: £{rental_stats['avg_monthly_rent']:,.0f}/mo")
                    for rc in live_data.get("rental_comps", [])[:10]:
                        sqft_str = f" | {rc['sqft']:.0f} sqft" if rc.get('sqft') else ""
                        st.write(f"• £{rc['rent']:,.0f}/mo — {rc['address'][:50]}...{sqft_str}")
                else:
                    st.warning("No rental comps found")
            
            if live_val.get("methods_used"):
                st.write("**Methods Used:** " + ", ".join(live_val["methods_used"]))
        else:
            st.info("Live data not fetched. Check 'Use Live Market Data' and enter a valid postcode.")

    with tab_facts:
        facts = result.get("extracted_facts", {})
        if facts:
            for k, v in facts.items():
                if v is not None and v != []:
                    if isinstance(v, list):
                        st.write(f"**{k.replace('_', ' ').title()}:**")
                        for item in v[:5]:
                            st.write(f"  • {item}")
                    else:
                        st.write(f"**{k.replace('_', ' ').title()}:** {v}")
        else:
            st.info("No PDF facts extracted. Enter details manually in the sidebar.")

    with tab_valuation:
        st.subheader("Fair Value Bands")
        vcols = st.columns(3)
        with vcols[0]:
            st.metric("Low", f"£{val['low_fair_value']:,.0f}")
        with vcols[1]:
            st.metric("Base", f"£{val['base_fair_value']:,.0f}")
        with vcols[2]:
            st.metric("High", f"£{val['high_fair_value']:,.0f}")

        st.write(f"**Margin vs Base:** {val['margin_pct']:.1f}%")
        st.write(f"**Flag:** {flag.upper()}")

    with tab_scenario:
        st.subheader("Scenario Table")
        st.table({
            "Item": [
                "Entry Price", "Capex Estimate", "Exit Valuation",
                "Gross Profit", "ROI", "Annualized ROI", "Max Bid", "Hold Period"
            ],
            "Value": [
                f"£{scen['entry_price']:,.0f}",
                f"£{scen['capex_estimate']:,.0f}",
                f"£{scen['exit_valuation']:,.0f}",
                f"£{scen['gross_profit']:,.0f}",
                f"{scen['roi_pct']:.1f}%",
                f"{scen['annualized_roi_pct']:.1f}%",
                f"£{scen['max_bid']:,.0f}",
                f"{scen['hold_period_years']} years",
            ],
        })

else:
    st.info("Enter deal details in the sidebar and click **Analyze** to begin.")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.caption("Real Estate DD Analyzer v1.0 | Built for Ali | OpenClaw Workspace")
