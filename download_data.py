#!/usr/bin/env python3
"""
Download trade and economic data for ITP presentation:
  Slide 3 - Mongolia:  mineral/coal export composition + China bilateral flows
  Slide 4 - Philippines:  remittances (% GDP) + manufactured-goods export share
  Slide 5 - Malaysia:  E&E vs. palm-oil/rubber export shift over time (2000-2024)

Sources
-------
  World Bank API   - macro/sectoral indicators (free, no key)
  WITS SDMX API    - bilateral + product-group trade flows (free, no key)
    wits.worldbank.org/API/V1/SDMX/V21/rest/
"""

import time
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path

DATA_DIR  = Path("data")
DATA_DIR.mkdir(exist_ok=True)

WB_BASE   = "https://api.worldbank.org/v2"
WITS_BASE = "https://wits.worldbank.org/API/V1/SDMX/V21/rest"
WITS_FLOW = "WBG_WITS,DF_WITS_TradeStats_Trade,1.0"

# -- helpers ------------------------------------------------------------------

def wb_fetch(countries: list[str], indicator: str, start=2000, end=2024) -> pd.DataFrame:
    """Fetch one World Bank WDI indicator for a list of ISO-3 countries."""
    url = f"{WB_BASE}/country/{';'.join(countries)}/indicator/{indicator}"
    params = {"format": "json", "per_page": 1000, "date": f"{start}:{end}"}
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()
    except Exception as e:
        print(f"    [WARN] WB {indicator}: {e}")
        return pd.DataFrame()
    if len(payload) < 2 or not payload[1]:
        return pd.DataFrame()
    records = [
        {"country": d["country"]["value"], "iso3": d["countryiso3code"],
         "year": int(d["date"]), "value": d["value"]}
        for d in payload[1] if d["value"] is not None
    ]
    return pd.DataFrame(records).sort_values(["country", "year"]).reset_index(drop=True)


def wits_fetch(
    reporter: str,
    partner: str = "WLD",
    product: str = "Total",
    start: int = 2000,
    end: int = 2023,
    indicator: str = "XPRT-TRD-VL",
) -> pd.DataFrame:
    """
    Fetch trade statistics from WITS SDMX API.

    reporter / partner - ISO-3 country code  (e.g. "MNG", "MYS") or "WLD" for world
    product  - WITS aggregate product code.  Available codes:
               Total, 27-27_Fuels, 25-26_Minerals, OresMtls, Fuels,
               84-85_MachElec, manuf, AgrRaw, Food, ...
    Values returned are in thousands USD.
    """
    key = f"A.{reporter}.{partner}.{product}.{indicator}"
    url = f"{WITS_BASE}/data/{WITS_FLOW}/{key}/"
    params = {"startperiod": str(start), "endperiod": str(end)}
    try:
        r = requests.get(url, params=params, timeout=45)
        r.raise_for_status()
    except Exception as e:
        print(f"    [WARN] WITS {key}: {e}")
        return pd.DataFrame()

    root = ET.fromstring(r.content)
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]

    rows = []
    for series in root.iter("Series"):
        keys = {kv.get("id"): kv.get("value") for kv in series.iter("Value")}
        for obs in series.iter("Obs"):
            period = obs.find("ObsDimension")
            val    = obs.find("ObsValue")
            if period is not None and val is not None:
                row = dict(keys)
                row["year"]      = int(period.get("value"))
                row["value_kusd"] = float(val.get("value"))
                rows.append(row)

    return (
        pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
        if rows else pd.DataFrame()
    )


def save(df: pd.DataFrame, filename: str) -> None:
    if df.empty:
        print(f"    [SKIP] {filename} - no data returned")
        return
    path = DATA_DIR / filename
    df.to_csv(path, index=False)
    print(f"    -> {path}  ({len(df)} rows)")


# =============================================================================
# 1. World Bank macro / sectoral indicators  (2000-2024)
# =============================================================================

print("\n=== World Bank indicators ===")

COUNTRIES = ["MNG", "PHL", "MYS"]

WB_INDICATORS = {
    # Merchandise export composition (% of total merchandise exports)
    "TX.VAL.MRCH.CD.WT":   "merchandise_exports_usd",
    "TX.VAL.MANF.ZS.UN":   "manufactures_pct_exports",
    "TX.VAL.FUEL.ZS.UN":   "fuel_pct_exports",        # coal is Mongolia's main fuel
    "TX.VAL.MMTL.ZS.UN":   "ores_metals_pct_exports", # copper, iron ore etc.
    "TX.VAL.AGRI.ZS.UN":   "agri_raw_pct_exports",
    # High-tech / ICT exports (Malaysia slide)
    "TX.VAL.TECH.MF.ZS":   "hightech_pct_manufactured_exports",
    "TX.VAL.ICTG.ZS.UN":   "ict_goods_pct_exports",   # ~E&E share
    # Philippines - remittances
    "BX.TRF.PWKR.DT.GD.ZS": "remittances_pct_gdp",
    "BX.TRF.PWKR.CD.DT":    "remittances_usd",
    # GDP (denominator / context)
    "NY.GDP.MKTP.CD": "gdp_usd",
    "NY.GDP.PCAP.CD": "gdp_per_capita_usd",
    # Net migration (Philippines labor-export story)
    "SM.POP.NETM": "net_migration",
}

frames = []
for code, name in WB_INDICATORS.items():
    print(f"  {code}  ({name})")
    df = wb_fetch(COUNTRIES, code)
    if not df.empty:
        df["indicator"] = name
        frames.append(df)
    time.sleep(0.6)

if frames:
    long_df = pd.concat(frames, ignore_index=True)
    save(long_df, "worldbank_long.csv")
    pivot = long_df.pivot_table(
        index=["country", "iso3", "year"], columns="indicator", values="value"
    ).reset_index()
    pivot.columns.name = None
    save(pivot, "worldbank_pivot.csv")


# =============================================================================
# 2. WITS SDMX  - bilateral and product-group trade flows
# =============================================================================

YEARS_RECENT = (2019, 2023)
YEARS_LONG   = (2000, 2023)
YEARS_EXTENDED = (1970, 2023)  # for Malaysia historical transition chart

# -- Mongolia ------------------------------------------------------------------
print("\n=== WITS - Mongolia ===")

print("  Total exports -> world (2000-2023)")
save(wits_fetch("MNG", "WLD", "Total",        *YEARS_LONG), "wits_mng_total_world.csv")
time.sleep(1)

print("  Total exports -> China (bilateral dependency, 2000-2023)")
save(wits_fetch("MNG", "CHN", "Total",        *YEARS_LONG), "wits_mng_total_china.csv")
time.sleep(1)

print("  Fuels (HS 27 = coal) -> world (2000-2023)")
save(wits_fetch("MNG", "WLD", "27-27_Fuels",  *YEARS_LONG), "wits_mng_fuels.csv")
time.sleep(1)

print("  Minerals (HS 25-26 = ores, copper) -> world (2000-2023)")
save(wits_fetch("MNG", "WLD", "25-26_Minerals", *YEARS_LONG), "wits_mng_minerals.csv")
time.sleep(1)

print("  Ores & Metals (WB classification) -> world (2000-2023)")
save(wits_fetch("MNG", "WLD", "OresMtls",     *YEARS_LONG), "wits_mng_oresmtls.csv")
time.sleep(1)

# -- Philippines ---------------------------------------------------------------
print("\n=== WITS - Philippines ===")

print("  Total exports -> world (2000-2023)")
save(wits_fetch("PHL", "WLD", "Total",           *YEARS_LONG), "wits_phl_total_world.csv")
time.sleep(1)

print("  Machinery & Electronics (HS 84-85) -> world (2000-2023)")
save(wits_fetch("PHL", "WLD", "84-85_MachElec",  *YEARS_LONG), "wits_phl_machElec.csv")
time.sleep(1)

print("  Manufactures -> world (2000-2023)")
save(wits_fetch("PHL", "WLD", "manuf",            *YEARS_LONG), "wits_phl_manuf.csv")
time.sleep(1)

# -- Malaysia ------------------------------------------------------------------
print("\n=== WITS - Malaysia ===")

print("  Total exports -> world (2000-2023)")
save(wits_fetch("MYS", "WLD", "Total",           *YEARS_LONG), "wits_mys_total_world.csv")
time.sleep(1)

print("  Machinery & Electronics (HS 84-85, E&E) -> world (2000-2023)")
save(wits_fetch("MYS", "WLD", "84-85_MachElec",  *YEARS_LONG), "wits_mys_machElec.csv")
time.sleep(1)

print("  Fuels (HS 27 = petroleum) -> world (2000-2023)")
save(wits_fetch("MYS", "WLD", "27-27_Fuels",     *YEARS_LONG), "wits_mys_fuels.csv")
time.sleep(1)

print("  Manufactures -> world (2000-2023)")
save(wits_fetch("MYS", "WLD", "manuf",            *YEARS_LONG), "wits_mys_manuf.csv")
time.sleep(1)

print("  Agri Raw Materials (rubber, palm oil) -> world (2000-2023)")
save(wits_fetch("MYS", "WLD", "AgrRaw",           *YEARS_LONG), "wits_mys_agrraw.csv")
time.sleep(1)

print("  Food (palm oil derivatives) -> world (2000-2023)")
save(wits_fetch("MYS", "WLD", "Food",             *YEARS_LONG), "wits_mys_food.csv")
time.sleep(1)

print("  Total imports <- world (2000-2023)")
save(wits_fetch("MYS", "WLD", "Total",           *YEARS_LONG, indicator="MPRT-TRD-VL"), "wits_mys_import_total.csv")
time.sleep(1)

print("  E&E imports (HS 84-85) <- world (2000-2023)")
save(wits_fetch("MYS", "WLD", "84-85_MachElec",  *YEARS_LONG, indicator="MPRT-TRD-VL"), "wits_mys_import_machElec.csv")
time.sleep(1)

print("  Fuels imports (HS 27) <- world (2000-2023)")
save(wits_fetch("MYS", "WLD", "27-27_Fuels",     *YEARS_LONG, indicator="MPRT-TRD-VL"), "wits_mys_import_fuels.csv")
time.sleep(1)


# =============================================================================
# 3. Derived summary tables
# =============================================================================

print("\n=== Building derived tables ===")


def load(name):
    p = DATA_DIR / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


# Mongolia: China share of total exports (China dependency)
mng_world = load("wits_mng_total_world.csv")
mng_china = load("wits_mng_total_china.csv")
if not mng_world.empty and not mng_china.empty:
    merged = mng_world[["year", "value_kusd"]].rename(columns={"value_kusd": "world_kusd"}).merge(
        mng_china[["year", "value_kusd"]].rename(columns={"value_kusd": "china_kusd"}),
        on="year", how="inner"
    )
    merged["china_share_pct"] = (merged["china_kusd"] / merged["world_kusd"] * 100).round(1)
    save(merged, "derived_mng_china_dependency.csv")

# Mongolia: export composition (fuels + minerals as % of total)
mng_fuels = load("wits_mng_fuels.csv")
mng_mins  = load("wits_mng_minerals.csv")
if not mng_world.empty and not mng_fuels.empty:
    comp = mng_world[["year", "value_kusd"]].rename(columns={"value_kusd": "total_kusd"})
    comp = comp.merge(
        mng_fuels[["year", "value_kusd"]].rename(columns={"value_kusd": "fuels_kusd"}),
        on="year", how="left"
    )
    if not mng_mins.empty:
        comp = comp.merge(
            mng_mins[["year", "value_kusd"]].rename(columns={"value_kusd": "minerals_kusd"}),
            on="year", how="left"
        )
    for col in [c for c in ("fuels_kusd", "minerals_kusd") if c in comp.columns]:
        pct_col = col.replace("_kusd", "_pct")
        comp[pct_col] = (comp[col] / comp["total_kusd"] * 100).round(1)
    save(comp, "derived_mng_export_composition.csv")

# Philippines: remittances vs. GDP
if frames:
    phl_data = long_df[(long_df["iso3"] == "PHL") & (long_df["indicator"].isin(
        ["remittances_pct_gdp", "remittances_usd", "gdp_usd", "manufactures_pct_exports"]
    ))]
    phl_wide = phl_data.pivot_table(index="year", columns="indicator", values="value").reset_index()
    phl_wide.columns.name = None
    save(phl_wide, "derived_phl_remittances.csv")

# Philippines: E&E share of exports (MachElec / total)
phl_total    = load("wits_phl_total_world.csv")
phl_machElec = load("wits_phl_machElec.csv")
phl_manuf    = load("wits_phl_manuf.csv")
if not phl_total.empty and not phl_machElec.empty:
    phl_comp = phl_total[["year", "value_kusd"]].rename(columns={"value_kusd": "total_kusd"})
    for label, df_src in [("machElec_kusd", phl_machElec),
                           ("manuf_kusd",    phl_manuf)]:
        if not df_src.empty:
            phl_comp = phl_comp.merge(
                df_src[["year", "value_kusd"]].rename(columns={"value_kusd": label}),
                on="year", how="left"
            )
    for col in [c for c in phl_comp.columns if c.endswith("_kusd") and c != "total_kusd"]:
        pct_col = col.replace("_kusd", "_pct")
        phl_comp[pct_col] = (phl_comp[col] / phl_comp["total_kusd"] * 100).round(1)
    save(phl_comp, "derived_phl_export_composition.csv")

# Malaysia: E&E share of exports (MachElec / total)
mys_total    = load("wits_mys_total_world.csv")
mys_machElec = load("wits_mys_machElec.csv")
mys_fuels    = load("wits_mys_fuels.csv")
mys_agrraw   = load("wits_mys_agrraw.csv")
if not mys_total.empty and not mys_machElec.empty:
    mys_comp = mys_total[["year", "value_kusd"]].rename(columns={"value_kusd": "total_kusd"})
    for label, df_src in [("machElec_kusd", mys_machElec),
                           ("fuels_kusd",    mys_fuels),
                           ("agrraw_kusd",   mys_agrraw)]:
        if not df_src.empty:
            mys_comp = mys_comp.merge(
                df_src[["year", "value_kusd"]].rename(columns={"value_kusd": label}),
                on="year", how="left"
            )
    for col in [c for c in mys_comp.columns if c.endswith("_kusd") and c != "total_kusd"]:
        pct_col = col.replace("_kusd", "_pct")
        mys_comp[pct_col] = (mys_comp[col] / mys_comp["total_kusd"] * 100).round(1)
    save(mys_comp, "derived_mys_export_composition.csv")

# Malaysia: E&E intra-industry trade (imports + exports, HS 84-85)
mys_imp_total    = load("wits_mys_import_total.csv")
mys_imp_machElec = load("wits_mys_import_machElec.csv")
mys_imp_fuels    = load("wits_mys_import_fuels.csv")
if not mys_imp_total.empty and not mys_imp_machElec.empty:
    mys_trade = mys_total[["year", "value_kusd"]].rename(columns={"value_kusd": "export_total_kusd"})
    mys_trade = mys_trade.merge(
        mys_machElec[["year", "value_kusd"]].rename(columns={"value_kusd": "export_ee_kusd"}),
        on="year", how="left"
    )
    mys_trade = mys_trade.merge(
        mys_imp_total[["year", "value_kusd"]].rename(columns={"value_kusd": "import_total_kusd"}),
        on="year", how="left"
    )
    mys_trade = mys_trade.merge(
        mys_imp_machElec[["year", "value_kusd"]].rename(columns={"value_kusd": "import_ee_kusd"}),
        on="year", how="left"
    )
    if not mys_imp_fuels.empty:
        mys_trade = mys_trade.merge(
            mys_imp_fuels[["year", "value_kusd"]].rename(columns={"value_kusd": "import_fuels_kusd"}),
            on="year", how="left"
        )
    mys_trade["export_ee_pct"] = (mys_trade["export_ee_kusd"] / mys_trade["export_total_kusd"] * 100).round(1)
    mys_trade["import_ee_pct"] = (mys_trade["import_ee_kusd"] / mys_trade["import_total_kusd"] * 100).round(1)
    save(mys_trade, "derived_mys_ee_trade.csv")

# Malaysia: extended WB WDI composition (1970-2024) for historical transition chart
print("\n=== Extended WB data for Malaysia (1970-2024) ===")
MYS_WB_INDICATORS = {
    "TX.VAL.MANF.ZS.UN":   "manufactures_pct",
    "TX.VAL.FUEL.ZS.UN":   "fuel_pct",
    "TX.VAL.AGRI.ZS.UN":   "agri_raw_pct",
    "TX.VAL.MMTL.ZS.UN":   "ores_metals_pct",
}
mys_wb_frames = []
for code, name in MYS_WB_INDICATORS.items():
    print(f"  {code}  ({name})")
    df = wb_fetch(["MYS"], code, start=1970, end=2024)
    if not df.empty:
        df = df.rename(columns={"value": name})[["year", name]]
        mys_wb_frames.append(df)
    time.sleep(0.6)
if mys_wb_frames:
    from functools import reduce
    mys_wb_comp = reduce(lambda a, b: a.merge(b, on="year", how="outer"), mys_wb_frames)
    mys_wb_comp = mys_wb_comp.sort_values("year").reset_index(drop=True)
    save(mys_wb_comp, "derived_mys_export_composition_extended.csv")

# Malaysia: FDI inflows + manufactures % (1970-2024) for FDI-E&E narrative
print("\n=== Malaysia FDI data (1970-2024) ===")
MYS_FDI_INDICATORS = {
    "BX.KLT.DINV.CD.WD":    "fdi_inflows_usd",
    "BX.KLT.DINV.WD.GD.ZS": "fdi_pct_gdp",
    "TX.VAL.MANF.ZS.UN":    "manufactures_pct",
}
mys_fdi_frames = []
for code, name in MYS_FDI_INDICATORS.items():
    print(f"  {code}  ({name})")
    df = wb_fetch(["MYS"], code, start=1970, end=2024)
    if not df.empty:
        df = df.rename(columns={"value": name})[["year", name]]
        mys_fdi_frames.append(df)
    time.sleep(0.6)
if mys_fdi_frames:
    from functools import reduce
    mys_fdi = reduce(lambda a, b: a.merge(b, on="year", how="outer"), mys_fdi_frames)
    mys_fdi = mys_fdi.sort_values("year").reset_index(drop=True)
    save(mys_fdi, "derived_mys_fdi.csv")


# Mongolia: commodity vulnerability (GDP growth + export revenue swings)
print("\n=== Mongolia commodity vulnerability data (2000-2024) ===")
MNG_VULN_INDICATORS = {
    "NY.GDP.MKTP.KD.ZG":   "gdp_growth_pct",
    "NY.GDP.MKTP.CD":      "gdp_usd",
    "TX.VAL.MRCH.CD.WT":   "merchandise_exports_usd",
}
mng_vuln_frames = []
for code, name in MNG_VULN_INDICATORS.items():
    print(f"  {code}  ({name})")
    df = wb_fetch(["MNG"], code, start=2000, end=2024)
    if not df.empty:
        df = df.rename(columns={"value": name})[["year", name]]
        mng_vuln_frames.append(df)
    time.sleep(0.6)
if mng_vuln_frames:
    from functools import reduce
    mng_vuln = reduce(lambda a, b: a.merge(b, on="year", how="outer"), mng_vuln_frames)
    mng_vuln = mng_vuln.sort_values("year").reset_index(drop=True)
    mng_vuln["export_yoy_pct"] = mng_vuln["merchandise_exports_usd"].pct_change() * 100
    save(mng_vuln, "derived_mng_commodity_vulnerability.csv")

# Commodity prices: coal & copper (Mongolia's key exports)
# Source: IMF Primary Commodity Prices via FRED (Federal Reserve Economic Data)
import io
print("\n=== Commodity prices (FRED / IMF, 2000-2024) ===")
FRED_SERIES = {
    "PCOALAUUSDM": "coal_price_usd_ton",
    "PCOPPUSDM":   "copper_price_usd_ton",
}
price_frames = []
for sid, name in FRED_SERIES.items():
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd=2000-01-01&coed=2024-12-01&fq=Annual&fam=avg"
    print(f"  {sid}  ({name})")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df["year"] = pd.to_datetime(df["observation_date"]).dt.year
        df = df.rename(columns={sid: name})
        df[name] = pd.to_numeric(df[name], errors="coerce")
        price_frames.append(df[["year", name]].dropna())
    except Exception as e:
        print(f"    [WARN] {sid}: {e}")
    time.sleep(0.6)
if price_frames:
    from functools import reduce
    prices = reduce(lambda a, b: a.merge(b, on="year", how="outer"), price_frames)
    prices = prices.sort_values("year").reset_index(drop=True)
    save(prices, "derived_commodity_prices.csv")


# =============================================================================
# 4. File summary
# =============================================================================

print("\n=== Downloaded files ===")
for f in sorted(DATA_DIR.iterdir()):
    try:
        rows = sum(1 for _ in open(f, encoding="utf-8")) - 1
        print(f"  {f.name:<55}  {rows:>5} rows")
    except Exception:
        print(f"  {f.name}")

print("\nDone. All files saved to data/")
