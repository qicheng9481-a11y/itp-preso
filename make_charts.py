#!/usr/bin/env python3
"""
Generate presentation charts from downloaded trade data.

Charts produced (saved to charts/):
  chart_mng_export_composition.png  -- Slide 3: Mongolia stacked bar
  chart_mng_china_dependency.png    -- Slide 3: bilateral China share
  chart_phl_remittances.png         -- Slide 4: Philippines remittances % GDP
  chart_phl_export_composition.png  -- Slide 4: manufactures vs. primary
  chart_mys_ee_transition.png       -- Slide 5: Malaysia E&E shift 1970-2024
  chart_mys_fdi.png                 -- Slide 5b: Malaysia FDI → E&E narrative
  chart_mys_ee_intra_industry.png   -- Slide 5c: E&E intra-industry trade
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
pivot    = pd.read_csv(DATA_DIR / "worldbank_pivot.csv")
mng_dep  = pd.read_csv(DATA_DIR / "derived_mng_china_dependency.csv")
mng_exp  = pd.read_csv(DATA_DIR / "derived_mng_export_composition.csv")
mng_vuln = pd.read_csv(DATA_DIR / "derived_mng_commodity_vulnerability.csv")
comm_px  = pd.read_csv(DATA_DIR / "derived_commodity_prices.csv")
mys_exp = pd.read_csv(DATA_DIR / "derived_mys_export_composition.csv")
mys_ext = pd.read_csv(DATA_DIR / "derived_mys_export_composition_extended.csv")
mys_fdi = pd.read_csv(DATA_DIR / "derived_mys_fdi.csv")
mys_trade = pd.read_csv(DATA_DIR / "derived_mys_ee_trade.csv")
phl_rem = pd.read_csv(DATA_DIR / "derived_phl_remittances.csv")
phl_exp = pd.read_csv(DATA_DIR / "derived_phl_export_composition.csv")


# =============================================================================
# Chart 1 – Mongolia: export composition stacked bar
# =============================================================================
print("Generating charts...")

def chart_mng_export_composition():
    mng = pivot[pivot["iso3"] == "MNG"].sort_values("year")
    # Use World Bank percentages; start after the 2008-2012 data gap
    mng = mng.dropna(subset=["fuel_pct_exports", "ores_metals_pct_exports"])
    mng = mng[mng["year"] >= 2013]
    years = mng["year"].values
    fuel  = mng["fuel_pct_exports"].values
    ores  = mng["ores_metals_pct_exports"].values
    manuf = mng["manufactures_pct_exports"].fillna(0).values
    agri  = mng["agri_raw_pct_exports"].fillna(0).values
    other = np.clip(100 - fuel - ores - manuf - agri, 0, 100)

    fig, ax = plt.subplots(figsize=(11, 7.5))
    w = 0.7

    b1 = ax.bar(years, fuel,  w, label="Coal & Fuels (HS 27)",         color=C["coal"])
    b2 = ax.bar(years, ores,  w, bottom=fuel,         label="Ores & Metals (HS 25-26)",  color=C["ores"])
    b3 = ax.bar(years, manuf, w, bottom=fuel+ores,    label="Manufactures",               color=C["manuf"])
    b4 = ax.bar(years, agri,  w, bottom=fuel+ores+manuf, label="Agri Raw",               color=C["agrraw"])
    b5 = ax.bar(years, other, w, bottom=fuel+ores+manuf+agri, label="Other",             color=C["other"])

    # Annotate combined mineral share on recent years
    for i in range(len(years)):
        mineral = fuel[i] + ores[i]
        if mineral > 60:
            ax.text(years[i], mineral + 1.5, f"{mineral:.0f}%",
                    ha="center", va="bottom", fontsize=8.5, color="#222222", fontweight="bold")

    ax.set_title("Mongolia: Merchandise Export Composition (2013–)", fontsize=14, fontweight="bold", pad=10)
    ax.set_ylabel("Share of Total Merchandise Exports (%)")
    ax.set_ylim(0, 107)
    pct_fmt(ax)
    ax.set_xticks(years)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.06), framealpha=0, fontsize=10, ncol=5)
    src(ax, "World Bank WDI (TX.VAL.FUEL.ZS.UN, TX.VAL.MMTL.ZS.UN, TX.VAL.MANF.ZS.UN, TX.VAL.AGRI.ZS.UN)", y=-0.24)
    fig.tight_layout()
    save(fig, "chart_mng_export_composition.png")


# =============================================================================
# Chart 2 – Mongolia: China dependency (dual-axis)
# =============================================================================

def chart_mng_china_dependency():
    dep = mng_dep[mng_dep["year"] >= 2013].copy()

    fig, ax1 = plt.subplots(figsize=(7, 11))
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
    ax1.legend(h1 + h2, l1 + l2, loc="upper center", bbox_to_anchor=(0.5, -0.06),
               framealpha=0, fontsize=10, ncol=3)
    ax1.grid(axis="y", alpha=0.25)
    src(ax1, "WITS TradeStats, Total exports, MNG→WLD & MNG→CHN (via World Bank SDMX)", y=-0.13)
    fig.tight_layout()
    save(fig, "chart_mng_china_dependency.png")


# =============================================================================
# Chart 2b – Mongolia: commodity vulnerability (export swings & GDP growth)
# =============================================================================

def chart_mng_commodity_vulnerability():
    df = mng_vuln.merge(comm_px, on="year", how="inner").sort_values("year")
    df = df.dropna(subset=["merchandise_exports_usd", "coal_price_usd_ton"])

    years   = df["year"].values
    exports = df["merchandise_exports_usd"].values / 1e9   # billions USD
    coal    = df["coal_price_usd_ton"].values
    copper  = df["copper_price_usd_ton"].values / 1000     # thousands USD/ton
    gdp_g   = df["gdp_growth_pct"].values

    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(6, 9),
                                          gridspec_kw={"height_ratios": [1, 1],
                                                       "hspace": 0.4})

    # ── Top panel: commodity prices ──
    ax_coal = ax_top
    ax_cu   = ax_top.twinx()

    ax_coal.fill_between(years, coal, alpha=0.15, color=C["coal"])
    ax_coal.plot(years, coal, "s-", color=C["coal"], lw=2.2, ms=5,
                 label="Coal price (left)")
    ax_cu.plot(years, copper, "o-", color=C["ores"], lw=2.2, ms=5,
               label="Copper price (right)")

    ax_coal.set_ylabel("Coal (USD / metric ton)", color=C["coal"], fontsize=10)
    ax_coal.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"${x:.0f}"))
    ax_coal.tick_params(axis="y", colors=C["coal"])
    ax_coal.spines["left"].set_color(C["coal"])

    ax_cu.set_ylabel("Copper (× $1 000 / metric ton)", color=C["ores"], fontsize=10)
    ax_cu.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"${x:.0f}k"))
    ax_cu.tick_params(axis="y", colors=C["ores"])
    ax_cu.spines["right"].set_visible(True)
    ax_cu.spines["right"].set_color(C["ores"])
    ax_cu.spines["top"].set_visible(False)

    ax_top.set_title("Global Commodity Prices", fontsize=12, fontweight="bold", pad=6)
    h1, l1 = ax_coal.get_legend_handles_labels()
    h2, l2 = ax_cu.get_legend_handles_labels()
    ax_coal.legend(h1 + h2, l1 + l2, loc="upper left", framealpha=0.8, fontsize=9)

    # ── Bottom panel: Mongolia exports + GDP growth ──
    ax_exp = ax_bot
    ax_gdp = ax_bot.twinx()

    ax_exp.bar(years, exports, 0.6, color=C["coal"], alpha=0.65,
               label="Merchandise exports (left)")
    ax_gdp.plot(years, gdp_g, "o-", color=C["world"], lw=2.5, ms=5,
                label="Real GDP growth (right)", zorder=5)
    ax_gdp.axhline(0, color="#999999", lw=0.8, ls="--")

    ax_exp.set_ylabel("Exports (USD billions)", color=C["coal"], fontsize=10)
    ax_exp.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"${x:.0f}B"))
    ax_exp.tick_params(axis="y", colors=C["coal"])
    ax_exp.spines["left"].set_color(C["coal"])

    ax_gdp.set_ylabel("Real GDP Growth (%)", color=C["world"], fontsize=10)
    ax_gdp.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{x:+.0f}%"))
    ax_gdp.tick_params(axis="y", colors=C["world"])
    ax_gdp.spines["right"].set_visible(True)
    ax_gdp.spines["right"].set_color(C["world"])
    ax_gdp.spines["top"].set_visible(False)

    ax_bot.set_title("Mongolia: Exports & GDP Growth", fontsize=12,
                     fontweight="bold", pad=6)
    h3, l3 = ax_exp.get_legend_handles_labels()
    h4, l4 = ax_gdp.get_legend_handles_labels()
    ax_exp.legend(h3 + h4, l3 + l4, loc="upper left", framealpha=0.8, fontsize=9)

    fig.suptitle("Mongolia: Vulnerability to Commodity Price Shocks",
                 fontsize=14, fontweight="bold", y=1.0)
    src(ax_bot, "FRED: PCOALAUUSDM, PCOPPUSDM (IMF Primary Commodity Prices)", y=-0.20)
    src(ax_bot, "World Bank WDI (NY.GDP.MKTP.KD.ZG, TX.VAL.MRCH.CD.WT)", y=-0.28)
    fig.tight_layout()
    save(fig, "chart_mng_commodity_vulnerability.png")


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
    # ── Top panel: WB WDI broad composition (2000–2024) ──
    wb = pivot[pivot["iso3"] == "PHL"].sort_values("year").copy()
    wb = wb.dropna(subset=["manufactures_pct_exports"])
    wb_years = wb["year"].values
    wb_manuf = wb["manufactures_pct_exports"].values
    wb_fuel  = wb["fuel_pct_exports"].fillna(0).values
    wb_ores  = wb["ores_metals_pct_exports"].fillna(0).values
    wb_agri  = wb["agri_raw_pct_exports"].fillna(0).values
    wb_primary = wb_fuel + wb_ores + wb_agri
    wb_other   = np.clip(100 - wb_manuf - wb_primary, 0, 100)

    # ── Bottom panel: WITS E&E breakdown (2000–2023, single source) ──
    wits = phl_exp.sort_values("year").copy().dropna(subset=["machElec_pct"])
    w_years     = wits["year"].values
    w_ee        = wits["machElec_pct"].values
    w_manuf     = wits["manuf_pct"].fillna(0).values
    w_other_mfg = np.clip(w_manuf - w_ee, 0, 100)
    w_rest      = np.clip(100 - w_manuf, 0, 100)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7.5),
                                    gridspec_kw={"height_ratios": [1, 1],
                                                 "hspace": 0.62})

    # ── Top panel: stacked bar ──
    w = 0.7
    ax1.bar(wb_years, wb_manuf,   w, label="Manufactures (incl. E&E)", color=C["manuf"])
    ax1.bar(wb_years, wb_primary, w, bottom=wb_manuf,
            label="Fuels + Ores + Agri Raw", color=C["primary"])
    ax1.bar(wb_years, wb_other,   w, bottom=wb_manuf + wb_primary,
            label="Other (food, services goods)", color=C["other"])

    for i in range(len(wb_years)):
        if wb_years[i] % 4 == 0 and wb_manuf[i] > 0:
            ax1.text(wb_years[i], wb_manuf[i] / 2, f"{wb_manuf[i]:.0f}%",
                     ha="center", va="center", fontsize=8, color="white", fontweight="bold")

    ax1.set_title("Broad Export Composition (World Bank WDI, 2000–2024)",
                  fontsize=11, fontweight="bold", pad=6)
    ax1.set_ylabel("Share of Exports (%)", fontsize=9)
    ax1.set_ylim(0, 105)
    pct_fmt(ax1)
    ax1.set_xticks(wb_years[::2])
    ax1.tick_params(labelsize=8)
    ax1.legend(loc="lower left", bbox_to_anchor=(0, 1.06),
               framealpha=0.75, fontsize=8, ncol=1)
    src(ax1, "World Bank WDI (TX.VAL.MANF.ZS.UN, TX.VAL.FUEL.ZS.UN, TX.VAL.MMTL.ZS.UN, TX.VAL.AGRI.ZS.UN)", y=-0.22)

    # ── Bottom panel: WITS E&E breakdown (stacked bar) ──
    C_other_mfg = "#5DADE2"
    ax2.bar(w_years, w_ee,        w, label="E&E: Machinery & Electronics (HS 84-85)", color=C["ee"])
    ax2.bar(w_years, w_other_mfg, w, bottom=w_ee,
            label="Other Manufactures", color=C_other_mfg)
    ax2.bar(w_years, w_rest,      w, bottom=w_ee + w_other_mfg,
            label="Non-Manufactures", color=C["other"])

    for i in range(len(w_years)):
        if w_years[i] % 4 == 0 and w_ee[i] > 0:
            ax2.text(w_years[i], w_ee[i] / 2, f"{w_ee[i]:.0f}%",
                     ha="center", va="center", fontsize=8, color="white", fontweight="bold")

    ax2.set_title("E&E Breakdown (WITS TradeStats, 2000–2023)",
                  fontsize=11, fontweight="bold", pad=6)
    ax2.set_ylabel("Share of Exports (%)", fontsize=9)
    ax2.set_ylim(0, 105)
    pct_fmt(ax2)
    ax2.set_xticks(w_years[::2])
    ax2.tick_params(labelsize=8)
    ax2.legend(loc="lower left", bbox_to_anchor=(0, 1.06),
               framealpha=0.75, fontsize=8, ncol=1)
    src(ax2, "WITS TradeStats (84-85_MachElec, manuf; PHL→WLD)", y=-0.20)

    fig.suptitle("Philippines: Merchandise Export Composition",
                 fontsize=13, fontweight="bold", y=1.0)
    fig.tight_layout(rect=[0, 0.02, 1, 0.97])
    save(fig, "chart_phl_export_composition.png")


# =============================================================================
# Chart 5 – Malaysia: E&E export shift (stacked area, 2000-2023)
# =============================================================================

def chart_mys_ee_transition():
    # ── Top panel data: WB WDI broad composition (1970–2024) ──
    wb = mys_ext.sort_values("year").copy().dropna(subset=["manufactures_pct"])
    wb_years     = wb["year"].values
    wb_manuf     = wb["manufactures_pct"].values
    wb_fuels     = wb["fuel_pct"].fillna(0).values
    wb_agr       = wb["agri_raw_pct"].fillna(0).values
    wb_ores      = wb["ores_metals_pct"].fillna(0).values
    wb_other     = np.clip(100 - wb_manuf - wb_fuels - wb_agr - wb_ores, 0, 100)

    # ── Bottom panel data: WITS E&E breakdown (2000–2023) ──
    wits = mys_exp.sort_values("year").copy().dropna(subset=["machElec_pct"])
    # Merge with WB manufactures to compute "other manufactures"
    wits = wits.merge(
        wb[["year", "manufactures_pct"]], on="year", how="inner"
    )
    w_years      = wits["year"].values
    w_ee         = wits["machElec_pct"].values
    w_other_mfg  = np.clip(wits["manufactures_pct"].values - w_ee, 0, 100)
    w_fuels      = wits["fuels_pct"].fillna(0).values
    w_agr        = wits["agrraw_pct"].fillna(0).values
    w_rest       = np.clip(100 - w_ee - w_other_mfg - w_fuels - w_agr, 0, 100)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 6.5),
                                    gridspec_kw={"height_ratios": [1, 1],
                                                 "hspace": 0.38})

    # ── Top panel: WB WDI stacked area (1970–2024) ──
    ax1.stackplot(wb_years,
                  wb_manuf, wb_fuels, wb_agr, wb_ores, wb_other,
                  labels=["Manufactures (incl. E&E)",
                          "Fuels / Petroleum",
                          "Agri Raw: Rubber, Timber & Palm Oil",
                          "Ores & Metals (Tin, etc.)",
                          "Other"],
                  colors=[C["ee"], C["fuels"], C["agrraw"], "#7F8C8D", C["other"]],
                  alpha=0.85)

    for yr_mark in [1975, 1985, 1995, 2010, 2023]:
        idx = np.searchsorted(wb_years, yr_mark)
        if idx < len(wb_years):
            ax1.annotate(f"{wb_manuf[idx]:.0f}%",
                         xy=(wb_years[idx], wb_manuf[idx] / 2),
                         ha="center", va="center",
                         fontsize=9, fontweight="bold", color="white")

    for yr_mark in [1970, 1980]:
        idx = np.searchsorted(wb_years, yr_mark)
        if idx < len(wb_years):
            base = wb_manuf[idx] + wb_fuels[idx]
            ax1.annotate(f"{wb_agr[idx]:.0f}%",
                         xy=(wb_years[idx], base + wb_agr[idx] / 2),
                         ha="center", va="center",
                         fontsize=9, fontweight="bold", color="white")

    ax1.axvspan(1986, 1991, alpha=0.08, color="#2C3E50", zorder=0)
    ax1.annotate("Structural shift",
                 xy=(1988.5, 93), ha="center", fontsize=8,
                 color="#2C3E50", fontstyle="italic")

    ax1.set_title("Broad Export Composition (World Bank WDI, 1970–2024)",
                  fontsize=11, fontweight="bold", pad=6)
    ax1.set_ylabel("Share of Exports (%)", fontsize=9)
    ax1.set_ylim(0, 100)
    pct_fmt(ax1)
    ax1.tick_params(labelsize=8)
    ax1.set_xlim(wb_years[0] - 0.5, wb_years[-1] + 0.5)
    ax1.legend(loc="center left", bbox_to_anchor=(1.01, 0.5),
               framealpha=0.75, fontsize=8)
    src(ax1, "World Bank WDI (TX.VAL.MANF.ZS.UN, TX.VAL.FUEL.ZS.UN, TX.VAL.AGRI.ZS.UN, TX.VAL.MMTL.ZS.UN)", y=-0.22)

    # ── Bottom panel: WITS E&E breakdown (2000–2023) ──
    C_other_mfg = "#5DADE2"
    ax2.stackplot(w_years,
                  w_ee, w_other_mfg, w_fuels, w_agr, w_rest,
                  labels=["E&E: Machinery & Electronics (HS 84-85)",
                          "Other Manufactures",
                          "Fuels / Petroleum (HS 27)",
                          "Agri Raw: Rubber & Palm Oil",
                          "Other"],
                  colors=[C["ee"], C_other_mfg, C["fuels"], C["agrraw"], C["other"]],
                  alpha=0.85)

    # Annotate E&E share
    for yr_mark in [2002, 2010, 2022]:
        idx = np.searchsorted(w_years, yr_mark)
        if idx < len(w_years):
            ax2.annotate(f"{w_ee[idx]:.0f}%",
                         xy=(w_years[idx], w_ee[idx] / 2),
                         ha="center", va="center",
                         fontsize=9, fontweight="bold", color="white")

    # Annotate "other manufactures" band
    idx_2005 = np.searchsorted(w_years, 2005)
    if idx_2005 < len(w_years):
        base = w_ee[idx_2005]
        ax2.annotate(f"{w_other_mfg[idx_2005]:.0f}%",
                     xy=(w_years[idx_2005], base + w_other_mfg[idx_2005] / 2),
                     ha="center", va="center",
                     fontsize=8, fontweight="bold", color="white")

    ax2.set_title("E&E Breakdown (WITS TradeStats, 2000–2023)",
                  fontsize=11, fontweight="bold", pad=6)
    ax2.set_ylabel("Share of Exports (%)", fontsize=9)
    ax2.set_ylim(0, 100)
    pct_fmt(ax2)
    ax2.tick_params(labelsize=8)
    ax2.set_xlim(w_years[0] - 0.5, w_years[-1] + 0.5)
    ax2.legend(loc="center left", bbox_to_anchor=(1.01, 0.5),
               framealpha=0.75, fontsize=8)
    src(ax2, "WITS TradeStats (84-85_MachElec, 27-27_Fuels, AgrRaw; MYS→WLD)", y=-0.20)

    fig.suptitle("Malaysia: From Resource Exports to E&E Dominance",
                 fontsize=13, fontweight="bold", y=1.0)
    fig.tight_layout(rect=[0, 0.02, 1, 0.97])
    save(fig, "chart_mys_ee_transition.png")


# =============================================================================
# Chart 5b – Malaysia: FDI inflows drove E&E transition (dual-axis)
# =============================================================================

def chart_mys_fdi():
    df = mys_fdi.sort_values("year").copy()
    df = df.dropna(subset=["fdi_inflows_usd", "manufactures_pct"])
    years    = df["year"].values
    fdi_usd  = df["fdi_inflows_usd"].values / 1e9   # billions
    fdi_pct  = df["fdi_pct_gdp"].values
    manuf    = df["manufactures_pct"].values

    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(9, 9),
                                          gridspec_kw={"height_ratios": [1, 1],
                                                       "hspace": 0.45})

    # ── Top panel: FDI inflows bar chart ──
    bar_colors = ["#1A5276" if 1986 <= y <= 2000 else "#85C1E9" for y in years]
    ax_top.bar(years, fdi_usd, 0.8, color=bar_colors, alpha=0.80)
    ax_top.axvspan(1986, 2000, alpha=0.06, color="#1A5276", zorder=0)
    ax_top.annotate("FDI surge era",
                    xy=(1993, max(fdi_usd) * 0.92), ha="center", fontsize=8,
                    color="#1A5276", fontstyle="italic")
    # Peak labels
    for yr_mark in [1992, 2021]:
        idx = list(years).index(yr_mark) if yr_mark in years else None
        if idx is not None:
            ax_top.annotate(f"${fdi_usd[idx]:.0f}B",
                            xy=(years[idx], fdi_usd[idx]),
                            xytext=(0, 5), textcoords="offset points",
                            ha="center", fontsize=7.5, fontweight="bold",
                            color="#1A5276")
    ax_top.set_ylabel("USD billions", fontsize=9)
    ax_top.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}B"))
    ax_top.set_ylim(0, max(fdi_usd) * 1.18)
    ax_top.set_title("FDI Net Inflows", fontsize=11, fontweight="bold", pad=6)
    ax_top.tick_params(labelsize=8)
    ax_top.set_xlim(1968, 2026)
    ax_top.set_xticks(range(1970, 2030, 10))

    # ── Bottom panel: Manufactures % of exports ──
    ax_bot.fill_between(years, manuf, alpha=0.15, color="#E74C3C")
    ax_bot.plot(years, manuf, "-", color="#E74C3C", lw=2.2)
    ax_bot.axvspan(1986, 2000, alpha=0.06, color="#1A5276", zorder=0)
    for yr_mark in [1980, 1993, 2024]:
        idx = list(years).index(yr_mark) if yr_mark in years else None
        if idx is not None:
            ax_bot.annotate(f"{manuf[idx]:.0f}%",
                            xy=(years[idx], manuf[idx]),
                            xytext=(6, -4), textcoords="offset points",
                            ha="left", fontsize=9, fontweight="bold",
                            color="#E74C3C")
    ax_bot.set_ylabel("% of merchandise exports", fontsize=9)
    ax_bot.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax_bot.set_ylim(0, 100)
    ax_bot.set_title("Manufactures Share of Exports", fontsize=11,
                     fontweight="bold", pad=6)
    ax_bot.tick_params(labelsize=8)
    ax_bot.set_xlim(1968, 2026)
    ax_bot.set_xticks(range(1970, 2030, 10))

    fig.suptitle("Malaysia: FDI & Manufacturing\nExport Transformation (1970–2024)",
                 fontsize=12, fontweight="bold", y=0.99)
    src(ax_bot, "World Bank WDI (BX.KLT.DINV.CD.WD, TX.VAL.MANF.ZS.UN)", y=-0.22)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    save(fig, "chart_mys_fdi.png")


# =============================================================================
# Chart 5c – Malaysia: E&E dominates both exports AND imports (intra-industry)
# =============================================================================

def chart_mys_ee_intra_industry():
    df = mys_trade.sort_values("year").copy()
    df = df.dropna(subset=["export_ee_pct", "import_ee_pct"])
    years      = df["year"].values
    exp_ee     = df["export_ee_pct"].values
    imp_ee     = df["import_ee_pct"].values
    exp_ee_usd = df["export_ee_kusd"].values / 1e6   # billions
    imp_ee_usd = df["import_ee_kusd"].values / 1e6

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5),
                                    gridspec_kw={"width_ratios": [1, 1],
                                                 "wspace": 0.30})

    # ── Left panel: E&E share of exports vs imports (%) ──
    ax1.plot(years, exp_ee, "o-", color=C["ee"], lw=2.5, ms=5,
             label="E&E as % of Exports")
    ax1.plot(years, imp_ee, "s--", color="#E74C3C", lw=2.5, ms=5,
             label="E&E as % of Imports")
    ax1.fill_between(years, exp_ee, imp_ee, alpha=0.08, color="#2C3E50")

    ax1.set_ylabel("E&E (HS 84-85) Share (%)", fontsize=10)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax1.set_ylim(0, 75)
    ax1.set_xlim(years[0] - 0.5, years[-1] + 0.5)
    ax1.set_title("E&E Share of Trade", fontsize=12, fontweight="bold", pad=8)
    ax1.legend(loc="upper right", framealpha=0.8, fontsize=9)

    # Annotate start & end values
    for arr, color, yoff in [(exp_ee, C["ee"], 6), (imp_ee, "#E74C3C", -14)]:
        ax1.annotate(f"{arr[0]:.0f}%", xy=(years[0], arr[0]),
                     xytext=(-8, yoff), textcoords="offset points",
                     ha="right", fontsize=9, fontweight="bold", color=color)
        ax1.annotate(f"{arr[-1]:.0f}%", xy=(years[-1], arr[-1]),
                     xytext=(8, yoff), textcoords="offset points",
                     ha="left", fontsize=9, fontweight="bold", color=color)

    ax1.text(0.5, 0.02,
             "E&E dominates both sides of trade →\n"
             "evidence of intra-industry trade in\n"
             "differentiated products",
             transform=ax1.transAxes, fontsize=8.5, color="#555555",
             ha="center", va="bottom", fontstyle="italic",
             bbox=dict(facecolor="white", alpha=0.7, edgecolor="none", pad=3))

    # ── Right panel: absolute E&E trade flows (USD billions) ──
    w = 0.35
    ax2.bar(years - w/2, exp_ee_usd, w, color=C["ee"], alpha=0.80,
            label="E&E Exports")
    ax2.bar(years + w/2, imp_ee_usd, w, color="#E74C3C", alpha=0.65,
            label="E&E Imports")

    ax2.set_ylabel("USD billions", fontsize=10)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}B"))
    ax2.set_xlim(years[0] - 1, years[-1] + 1)
    ax2.set_title("E&E Trade Volumes", fontsize=12, fontweight="bold", pad=8)
    ax2.legend(loc="upper left", framealpha=0.8, fontsize=9)

    # Annotate latest values
    ax2.annotate(f"${exp_ee_usd[-1]:.0f}B",
                 xy=(years[-1] - w/2, exp_ee_usd[-1]),
                 xytext=(0, 6), textcoords="offset points",
                 ha="center", fontsize=8, fontweight="bold", color=C["ee"])
    ax2.annotate(f"${imp_ee_usd[-1]:.0f}B",
                 xy=(years[-1] + w/2, imp_ee_usd[-1]),
                 xytext=(0, 6), textcoords="offset points",
                 ha="center", fontsize=8, fontweight="bold", color="#E74C3C")

    fig.suptitle(
        "Malaysia: E&E Dominates Both Exports and Imports — Intra-Industry Trade (2000–2023)",
        fontsize=13, fontweight="bold", y=1.0)
    src(ax1, "WITS TradeStats (84-85_MachElec; MYS exports & imports)")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    save(fig, "chart_mys_ee_intra_industry.png")


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
    src(ax, "World Bank WDI (TX.VAL.FUEL.ZS.UN, TX.VAL.MMTL.ZS.UN)", y=-0.18)

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
    src(ax, "World Bank WDI (BX.TRF.PWKR.DT.GD.ZS)", y=-0.18)

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
    src(ax, "WITS TradeStats (84-85_MachElec; MYS→WLD)", y=-0.18)

    fig.tight_layout()
    save(fig, "chart_synthesis.png")


# =============================================================================
# Run all charts
# =============================================================================

chart_mng_export_composition()
chart_mng_china_dependency()
chart_mng_commodity_vulnerability()
chart_phl_remittances()
chart_phl_export_composition()
chart_mys_ee_transition()
chart_mys_fdi()
chart_mys_ee_intra_industry()
chart_synthesis()

print(f"\nDone. {len(list(CHART_DIR.iterdir()))} charts saved to charts/")
