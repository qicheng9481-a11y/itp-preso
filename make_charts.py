#!/usr/bin/env python3
"""
Generate presentation charts from downloaded trade data.

Charts produced (saved to charts/):
  chart_mng_export_composition.png  -- Slide 3: Mongolia stacked bar
  chart_mng_china_dependency.png    -- Slide 3: bilateral China share
  chart_phl_remittances.png         -- Slide 4: Philippines remittances % GDP
  chart_phl_export_composition.png  -- Slide 4: manufactures vs. primary
  chart_mys_ee_transition.png       -- Slide 5: Malaysia E&E shift 2000-2023
  chart_synthesis.png               -- Slide 6: 3-panel comparison

Run: uv run --with pandas --with matplotlib python make_charts.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

DATA_DIR  = Path("data")
CHART_DIR = Path("charts")
CHART_DIR.mkdir(exist_ok=True)

# ── global style ──────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family":       "DejaVu Sans",
    "font.size":         12,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.grid":         True,
    "axes.grid.axis":    "y",
    "grid.alpha":        0.30,
    "grid.linestyle":    "--",
    "figure.dpi":        150,
    "savefig.dpi":       150,
    "savefig.bbox":      "tight",
    "savefig.facecolor": "white",
})

# Colour palette (consistent across all charts)
C = {
    "coal":    "#C0392B",   # deep red
    "ores":    "#E67E22",   # orange
    "manuf":   "#2980B9",   # steel blue
    "ee":      "#1A5276",   # dark navy (E&E)
    "fuels":   "#E67E22",   # orange (petroleum/fuels)
    "agrraw":  "#27AE60",   # green (rubber / palm oil)
    "food":    "#8BC34A",   # light green
    "remiit":  "#2980B9",   # blue (remittances)
    "primary": "#E74C3C",   # red (primary exports)
    "other":   "#BDC3C7",   # light grey
    "china":   "#C0392B",   # red (China flows)
    "world":   "#2980B9",   # blue (world total)
    "line":    "#2C3E50",   # near-black line
}


def src(ax, text, y=-0.16):
    ax.annotate(f"Source: {text}", xy=(0, y), xycoords="axes fraction",
                fontsize=8, color="#666666")


def pct_fmt(ax, axis="y"):
    fmt = mticker.FuncFormatter(lambda x, _: f"{x:.0f}%")
    if axis == "y":
        ax.yaxis.set_major_formatter(fmt)
    else:
        ax.xaxis.set_major_formatter(fmt)


def b_fmt(ax):
    """Format y axis in billions USD."""
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"${x/1e9:.0f}B")
    )


def save(fig, name):
    path = CHART_DIR / name
    fig.savefig(path)
    plt.close(fig)
    print(f"  -> {path}")


# ── load data ─────────────────────────────────────────────────────────────────
pivot   = pd.read_csv(DATA_DIR / "worldbank_pivot.csv")
mng_dep = pd.read_csv(DATA_DIR / "derived_mng_china_dependency.csv")
mng_exp = pd.read_csv(DATA_DIR / "derived_mng_export_composition.csv")
mys_exp = pd.read_csv(DATA_DIR / "derived_mys_export_composition.csv")
phl_rem = pd.read_csv(DATA_DIR / "derived_phl_remittances.csv")


# =============================================================================
# Chart 1 – Mongolia: export composition stacked bar
# =============================================================================
print("Generating charts...")

def chart_mng_export_composition():
    mng = pivot[pivot["iso3"] == "MNG"].sort_values("year")
    # Use World Bank percentages (longer series, 2000-2024)
    mng = mng.dropna(subset=["fuel_pct_exports", "ores_metals_pct_exports"])
    years = mng["year"].values
    fuel  = mng["fuel_pct_exports"].values
    ores  = mng["ores_metals_pct_exports"].values
    manuf = mng["manufactures_pct_exports"].fillna(0).values
    agri  = mng["agri_raw_pct_exports"].fillna(0).values
    other = np.clip(100 - fuel - ores - manuf - agri, 0, 100)

    fig, ax = plt.subplots(figsize=(11, 5))
    w = 0.7

    b1 = ax.bar(years, fuel,  w, label="Coal & Fuels (HS 27)",         color=C["coal"])
    b2 = ax.bar(years, ores,  w, bottom=fuel,         label="Ores & Metals (HS 25-26)",  color=C["ores"])
    b3 = ax.bar(years, manuf, w, bottom=fuel+ores,    label="Manufactures",               color=C["manuf"])
    b4 = ax.bar(years, agri,  w, bottom=fuel+ores+manuf, label="Agri Raw",               color=C["agrraw"])
    b5 = ax.bar(years, other, w, bottom=fuel+ores+manuf+agri, label="Other",             color=C["other"])

    # Annotate combined mineral share on recent years
    for i in range(len(years)):
        mineral = fuel[i] + ores[i]
        if mineral > 60 and years[i] >= 2017:
            ax.text(years[i], mineral + 1.5, f"{mineral:.0f}%",
                    ha="center", va="bottom", fontsize=8.5, color="#222222", fontweight="bold")

    ax.set_title("Mongolia: Merchandise Export Composition", fontsize=14, fontweight="bold", pad=10)
    ax.set_ylabel("Share of Total Merchandise Exports (%)")
    ax.set_ylim(0, 107)
    pct_fmt(ax)
    ax.set_xticks(years[::2])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.06), framealpha=0, fontsize=10, ncol=5)
    # Note the data gap in WB series
    ax.annotate("WB data\ngap",
                xy=(2010, 5), fontsize=8, color="#888888",
                ha="center", style="italic")
    src(ax, "World Bank WDI (TX.VAL.FUEL.ZS.UN, TX.VAL.MMTL.ZS.UN, TX.VAL.MANF.ZS.UN)", y=-0.24)
    fig.tight_layout()
    save(fig, "chart_mng_export_composition.png")


# =============================================================================
# Chart 2 – Mongolia: China dependency (dual-axis)
# =============================================================================

def chart_mng_china_dependency():
    dep = mng_dep.copy()

    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax2 = ax1.twinx()

    years = dep["year"].values
    world = dep["world_kusd"].values / 1e6    # billions USD
    china = dep["china_kusd"].values  / 1e6
    share = dep["china_share_pct"].values

    # Bars: world total (light) + China portion (red)
    w = 0.6
    ax1.bar(years, world, w, color=C["world"], alpha=0.35, label="Total exports (World, left)")
    ax1.bar(years, china, w, color=C["china"], alpha=0.80, label="Exports to China (left)")

    # Line: China share %
    ax2.plot(years, share, "o-", color=C["line"], lw=2, ms=5,
             label="China share (right)")
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("China's Share of Total Exports (%)", color=C["line"])
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax2.tick_params(axis="y", colors=C["line"])
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(C["line"])
    ax2.spines["top"].set_visible(False)

    # Annotate share %
    for yr, s in zip(years, share):
        if yr >= 2017:
            ax2.annotate(f"{s:.0f}%", xy=(yr, s),
                         xytext=(0, 8), textcoords="offset points",
                         ha="center", fontsize=9, color=C["line"])

    ax1.set_ylabel("Exports (USD billions, left)", color=C["world"])
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}B"))
    ax1.tick_params(axis="y", colors=C["world"])
    ax1.spines["left"].set_color(C["world"])
    ax1.set_title("Mongolia: Export Concentration Toward China", fontsize=14,
                  fontweight="bold", pad=10)

    # Combined legend
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", framealpha=0, fontsize=10)
    ax1.grid(axis="y", alpha=0.25)
    src(ax1, "WITS TradeStats (via World Bank SDMX)")
    fig.tight_layout()
    save(fig, "chart_mng_china_dependency.png")


# =============================================================================
# Chart 3 – Philippines: remittances % of GDP (line) + absolute (bar)
# =============================================================================

def chart_phl_remittances():
    df = phl_rem.dropna(subset=["remittances_pct_gdp", "remittances_usd"]).sort_values("year")
    years = df["year"].values
    pct   = df["remittances_pct_gdp"].values
    usd   = df["remittances_usd"].values       # in USD, convert to billions

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Left: % of GDP
    ax1.fill_between(years, pct, alpha=0.18, color=C["remiit"])
    ax1.plot(years, pct, "o-", color=C["remiit"], lw=2.2, ms=5)
    ax1.set_title("Remittances as % of GDP", fontsize=13, fontweight="bold")
    ax1.set_ylabel("Personal Remittances Received (% GDP)")
    pct_fmt(ax1)
    ax1.set_ylim(0, 14)
    # Highlight 2024
    latest = df[df["year"] == df["year"].max()].iloc[0]
    ax1.annotate(f"{latest.remittances_pct_gdp:.1f}%\n({int(latest.year)})",
                 xy=(latest.year, latest.remittances_pct_gdp),
                 xytext=(-35, 12), textcoords="offset points",
                 fontsize=10, fontweight="bold", color=C["remiit"],
                 arrowprops=dict(arrowstyle="-", color=C["remiit"], lw=1.2))
    src(ax1, "World Bank WDI (BX.TRF.PWKR.DT.GD.ZS)")

    # Right: absolute remittances in billion USD
    colors_bar = [C["remiit"] if y >= 2020 else "#85C1E9" for y in years]
    ax2.bar(years, usd / 1e9, color=colors_bar, width=0.7)
    ax2.set_title("Remittance Inflows (USD billions)", fontsize=13, fontweight="bold")
    ax2.set_ylabel("USD billions")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}B"))
    # Annotate latest bar
    ax2.text(latest.year, latest.remittances_usd / 1e9 + 0.3,
             f"${latest.remittances_usd/1e9:.1f}B",
             ha="center", fontsize=10, fontweight="bold", color=C["remiit"])
    src(ax2, "World Bank WDI (BX.TRF.PWKR.CD.DT)")

    fig.suptitle("Philippines: Labor Abundance via Migration", fontsize=15,
                 fontweight="bold", y=1.01)
    fig.tight_layout()
    save(fig, "chart_phl_remittances.png")


# =============================================================================
# Chart 4 – Philippines: export composition (manufactures vs. primary)
# =============================================================================

def chart_phl_export_composition():
    phl = pivot[pivot["iso3"] == "PHL"].sort_values("year")
    phl = phl.dropna(subset=["manufactures_pct_exports"])
    years = phl["year"].values
    manuf = phl["manufactures_pct_exports"].values
    fuel  = phl["fuel_pct_exports"].fillna(0).values
    ores  = phl["ores_metals_pct_exports"].fillna(0).values
    agri  = phl["agri_raw_pct_exports"].fillna(0).values
    primary = fuel + ores + agri
    other   = np.clip(100 - manuf - primary, 0, 100)

    fig, ax = plt.subplots(figsize=(11, 5))
    w = 0.7
    ax.bar(years, manuf,   w, label="Manufactures",                 color=C["manuf"])
    ax.bar(years, primary, w, bottom=manuf,        label="Fuels + Ores + Agri Raw",         color=C["primary"])
    ax.bar(years, other,   w, bottom=manuf+primary, label="Other (food, services goods)",    color=C["other"])

    # Annotate manufactures share — every other year only to avoid crowding
    for i in range(len(years)):
        if years[i] >= 2014 and years[i] % 2 == 0 and manuf[i] > 0:
            ax.text(years[i], manuf[i] / 2, f"{manuf[i]:.0f}%",
                    ha="center", va="center", fontsize=8.5, color="white", fontweight="bold")

    ax.set_title("Philippines: Merchandise Export Composition", fontsize=14,
                 fontweight="bold", pad=10)
    ax.set_ylabel("Share of Total Merchandise Exports (%)")
    ax.set_ylim(0, 105)
    pct_fmt(ax)
    ax.set_xticks(years[::2])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.06), framealpha=0, fontsize=10, ncol=3)
    src(ax, "World Bank WDI (TX.VAL.MANF.ZS.UN, TX.VAL.FUEL.ZS.UN, TX.VAL.MMTL.ZS.UN)", y=-0.24)
    fig.tight_layout()
    save(fig, "chart_phl_export_composition.png")


# =============================================================================
# Chart 5 – Malaysia: E&E export shift (stacked area, 2000-2023)
# =============================================================================

def chart_mys_ee_transition():
    df = mys_exp.sort_values("year")
    df = df.dropna(subset=["machElec_pct"])
    years     = df["year"].values
    ee_pct    = df["machElec_pct"].values
    fuels_pct = df["fuels_pct"].fillna(0).values
    agr_pct   = df["agrraw_pct"].fillna(0).values
    other_pct = np.clip(100 - ee_pct - fuels_pct - agr_pct, 0, 100)

    fig, ax = plt.subplots(figsize=(11, 5.5))

    # Stacked area
    ax.stackplot(years,
                 ee_pct, fuels_pct, agr_pct, other_pct,
                 labels=["Machinery & Electronics (HS 84-85)",
                         "Fuels / Petroleum (HS 27)",
                         "Agri Raw: Rubber & Palm Oil",
                         "Other"],
                 colors=[C["ee"], C["fuels"], C["agrraw"], C["other"]],
                 alpha=0.85)

    # Annotate E&E share at key years — keep labels away from edges
    for yr_mark, x_offset in [(2002, 12), (2010, 0), (2020, -12)]:
        idx = np.searchsorted(years, yr_mark)
        if idx < len(years):
            yr_actual = years[idx]
            ee_val    = ee_pct[idx]
            ax.annotate(f"{ee_val:.0f}%",
                        xy=(yr_actual, ee_val / 2),
                        xytext=(x_offset, 0), textcoords="offset points",
                        ha="center", va="center",
                        fontsize=10, fontweight="bold", color="white")

    # Note: Malaysia's palm-oil → E&E structural shift occurred in the 1970s-1990s;
    # this chart shows the sustained E&E dominance since 2000.
    ax.text(0.01, 0.96,
            "Note: E&E dominance pre-dates 2000; the palm oil/rubber → E&E shift\n"
            "occurred in the 1970s–1990s (data available from 2000 onward).",
            transform=ax.transAxes, fontsize=8, color="#555555",
            va="top", ha="left",
            bbox=dict(facecolor="white", alpha=0.7, edgecolor="none", pad=3))

    ax.set_title("Malaysia: Merchandise Export Composition — E&E Dominance (2000–2023)",
                 fontsize=13, fontweight="bold", pad=10)
    ax.set_ylabel("Share of Total Merchandise Exports (%)")
    ax.set_ylim(0, 100)
    pct_fmt(ax)
    ax.set_xlim(years[0] - 0.5, years[-1] + 0.5)
    ax.legend(loc="upper right", framealpha=0.75, fontsize=10)
    src(ax, "WITS TradeStats (via World Bank SDMX), product codes: 84-85_MachElec, 27-27_Fuels, AgrRaw")
    fig.tight_layout()
    save(fig, "chart_mys_ee_transition.png")


# =============================================================================
# Chart 6 – Synthesis: 3-panel "one-pager" for Slide 6
# =============================================================================

def chart_synthesis():
    # Panel data
    mng_wb = pivot[pivot["iso3"] == "MNG"].sort_values("year").dropna(
        subset=["fuel_pct_exports", "ores_metals_pct_exports"]
    )
    phl_wb = pivot[pivot["iso3"] == "PHL"].sort_values("year").dropna(
        subset=["remittances_pct_gdp"]
    )
    mys_d = mys_exp.sort_values("year").dropna(subset=["machElec_pct"])

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))
    fig.suptitle("Three Endowments, Three Trade Patterns: H-O in Action",
                 fontsize=15, fontweight="bold", y=1.01)

    # -- Panel 1: Mongolia mineral exports --
    ax = axes[0]
    fuel = mng_wb["fuel_pct_exports"].values
    ores = mng_wb["ores_metals_pct_exports"].values
    yrs  = mng_wb["year"].values
    mineral = fuel + ores
    ax.fill_between(yrs, mineral, alpha=0.25, color=C["coal"])
    ax.plot(yrs, mineral, "o-", color=C["coal"], lw=2, ms=4)
    ax.set_ylim(0, 105)
    pct_fmt(ax)
    ax.set_title("Mongolia\nCoal + Ores % of Exports", fontsize=12, fontweight="bold")
    ax.set_ylabel("Share of Merchandise Exports")
    ax.text(0.05, 0.92, "Resource-\nAbundant", transform=ax.transAxes,
            fontsize=9, color="#C0392B", fontstyle="italic")
    # Latest annotation
    ax.annotate(f"{mineral[-1]:.0f}%",
                xy=(yrs[-1], mineral[-1]),
                xytext=(-30, -15), textcoords="offset points",
                fontsize=10, fontweight="bold", color=C["coal"],
                arrowprops=dict(arrowstyle="-", color=C["coal"]))
    src(ax, "World Bank WDI", y=-0.18)

    # -- Panel 2: Philippines remittances % GDP --
    ax = axes[1]
    phl_d = phl_rem.dropna(subset=["remittances_pct_gdp"]).sort_values("year")
    yr_p  = phl_d["year"].values
    rem_p = phl_d["remittances_pct_gdp"].values
    ax.fill_between(yr_p, rem_p, alpha=0.25, color=C["remiit"])
    ax.plot(yr_p, rem_p, "o-", color=C["remiit"], lw=2, ms=4)
    ax.set_ylim(0, 14)
    pct_fmt(ax)
    ax.set_title("Philippines\nRemittances as % of GDP", fontsize=12, fontweight="bold")
    ax.set_ylabel("% of GDP")
    ax.text(0.05, 0.92, "Labor-\nAbundant", transform=ax.transAxes,
            fontsize=9, color=C["remiit"], fontstyle="italic")
    ax.annotate(f"{rem_p[-1]:.1f}%",
                xy=(yr_p[-1], rem_p[-1]),
                xytext=(-40, 5), textcoords="offset points",
                fontsize=10, fontweight="bold", color=C["remiit"],
                arrowprops=dict(arrowstyle="-", color=C["remiit"]))
    src(ax, "World Bank WDI", y=-0.18)

    # -- Panel 3: Malaysia E&E share --
    ax = axes[2]
    yr_m  = mys_d["year"].values
    ee_m  = mys_d["machElec_pct"].values
    ax.fill_between(yr_m, ee_m, alpha=0.25, color=C["ee"])
    ax.plot(yr_m, ee_m, "o-", color=C["ee"], lw=2, ms=4)
    ax.set_ylim(0, 70)
    pct_fmt(ax)
    ax.set_title("Malaysia\nE&E (HS 84-85) % of Exports", fontsize=12, fontweight="bold")
    ax.set_ylabel("Share of Merchandise Exports")
    ax.text(0.05, 0.92, "Capital/Skill-\nAbundant", transform=ax.transAxes,
            fontsize=9, color=C["ee"], fontstyle="italic")
    ax.annotate(f"{ee_m[-1]:.0f}%",
                xy=(yr_m[-1], ee_m[-1]),
                xytext=(-40, 5), textcoords="offset points",
                fontsize=10, fontweight="bold", color=C["ee"],
                arrowprops=dict(arrowstyle="-", color=C["ee"]))
    src(ax, "WITS TradeStats", y=-0.18)

    fig.tight_layout()
    save(fig, "chart_synthesis.png")


# =============================================================================
# Run all charts
# =============================================================================

chart_mng_export_composition()
chart_mng_china_dependency()
chart_phl_remittances()
chart_phl_export_composition()
chart_mys_ee_transition()
chart_synthesis()

print(f"\nDone. {len(list(CHART_DIR.iterdir()))} charts saved to charts/")
