"""
TelNova Communications - Operations Planning & Forecasting Engine
====================================================================
Mirrors the same rigor as the companion HR and Finance projects' planning
engines, applied to network operations:

1. INCIDENT VOLUME FORECAST
   - Holt's linear (double) exponential smoothing on monthly incident
     counts, projected forward 12 months.

2. SERVICE DEMAND FORECAST
   - 12-month linear-trend regression on field-service order volume,
     blended 50/50 with a stated subscriber-growth-aligned target.

3. CAPACITY EXHAUSTION PROJECTION
   - Linear trend on utilization % per region/network-type, projected
     forward to estimate months-to-exhaustion (crossing a 90% capacity
     threshold) -- a standard capacity-planning technique.

4. NETWORK RISK SCORE
   - Every region/network-type combination scored 0-100 with a
     transparent weighted-factor model: incident frequency, MTTR
     trend, capacity utilization level, and uptime trend. Min-max
     scaled, banded into Low/Medium/High/Critical -- fully explainable.

Author: Milad Shabani
"""

import numpy as np
import pandas as pd
from datetime import datetime

TODAY = datetime(2026, 9, 1)


# ----------------------------------------------------------------------
# 1. INCIDENT VOLUME FORECAST (Holt's linear exponential smoothing)
# ----------------------------------------------------------------------
def forecast_incident_volume(incidents_df, horizon_months=12, alpha=0.35, beta=0.25):
    monthly = incidents_df.groupby("Month").size().reset_index(name="IncidentCount")
    monthly["Month"] = pd.to_datetime(monthly["Month"])
    monthly = monthly.sort_values("Month").reset_index(drop=True)

    series = monthly["IncidentCount"].values
    level = series[0]
    trend = series[1] - series[0]
    for t in range(1, len(series)):
        last_level = level
        level = alpha * series[t] + (1 - alpha) * (level + trend)
        trend = beta * (level - last_level) + (1 - beta) * trend

    forecasts = [max(0, level + h * trend) for h in range(1, horizon_months + 1)]
    future_months = pd.date_range(start=monthly["Month"].max() + pd.offsets.MonthBegin(1), periods=horizon_months, freq="MS")
    return pd.DataFrame({"Month": future_months.date, "ForecastIncidentCount": np.round(forecasts, 0)})


# ----------------------------------------------------------------------
# 2. SERVICE DEMAND FORECAST
# ----------------------------------------------------------------------
def forecast_service_demand(orders_df, horizon_months=12, growth_target_annual=0.07):
    monthly = orders_df.groupby("Month").size().reset_index(name="OrderCount")
    monthly["Month"] = pd.to_datetime(monthly["Month"])
    monthly = monthly.sort_values("Month").tail(18).reset_index(drop=True)

    x = np.arange(len(monthly))
    y = monthly["OrderCount"].values
    slope, intercept = np.polyfit(x, y, 1)
    future_x = np.arange(len(monthly), len(monthly) + horizon_months)
    trend_forecast = intercept + slope * future_x

    last_actual = y[-1]
    growth_path = last_actual * (1 + growth_target_annual) ** (np.arange(1, horizon_months + 1) / 12)
    blended = 0.5 * trend_forecast + 0.5 * growth_path

    future_months = pd.date_range(start=monthly["Month"].max() + pd.offsets.MonthBegin(1), periods=horizon_months, freq="MS")
    return pd.DataFrame({
        "Month": future_months.date,
        "ForecastOrderCount_Trend": np.round(trend_forecast, 0),
        "ForecastOrderCount_GrowthTarget": np.round(growth_path, 0),
        "ForecastOrderCount_Blended": np.round(blended, 0),
    }), slope


# ----------------------------------------------------------------------
# 3. CAPACITY EXHAUSTION PROJECTION
# ----------------------------------------------------------------------
def forecast_capacity_exhaustion(capacity_df, threshold=0.90):
    rows = []
    for (region, ntype), grp in capacity_df.groupby(["Region", "NetworkType"]):
        grp = grp.sort_values("Month").tail(18).reset_index(drop=True)
        x = np.arange(len(grp))
        y = grp["UtilizationPct"].values
        slope, intercept = np.polyfit(x, y, 1)

        current_util = y[-1]
        if slope <= 0:
            months_to_exhaustion = None  # not trending toward exhaustion
        else:
            months_needed = (threshold - current_util) / slope
            months_to_exhaustion = round(months_needed, 1) if months_needed > 0 else 0

        rows.append(dict(
            Region=region, NetworkType=ntype, CurrentUtilizationPct=round(current_util, 4),
            MonthlyTrendPct=round(slope, 5), MonthsToExhaustion=months_to_exhaustion,
            ProjectedUtilizationIn12Mo=round(min(current_util + slope * 12, 1.0), 4),
        ))
    return pd.DataFrame(rows).sort_values("CurrentUtilizationPct", ascending=False).reset_index(drop=True)


# ----------------------------------------------------------------------
# 4. NETWORK RISK SCORE (per region x network type, explainable weighted model)
# ----------------------------------------------------------------------
def score_network_risk(incidents_df, uptime_df, capacity_df):
    combos = []
    for (region, ntype), grp in incidents_df.groupby(["Region", "NetworkType"]):
        grp = grp.sort_values("Month")
        monthly_counts = grp.groupby("Month").size()
        incident_freq = monthly_counts.mean()

        mttr_series = grp.groupby("Month")["ResolutionTimeMinutes"].mean()
        x = np.arange(len(mttr_series))
        mttr_trend = np.polyfit(x, mttr_series.values, 1)[0] if len(mttr_series) > 2 else 0

        up = uptime_df[(uptime_df["Region"] == region) & (uptime_df["NetworkType"] == ntype)].sort_values("Month")
        uptime_trend = np.polyfit(np.arange(len(up)), up["UptimePct"].values, 1)[0] if len(up) > 2 else 0

        cap = capacity_df[(capacity_df["Region"] == region) & (capacity_df["NetworkType"] == ntype)].sort_values("Month")
        latest_util = cap["UtilizationPct"].iloc[-1] if len(cap) else 0

        combos.append(dict(
            Region=region, NetworkType=ntype, AvgMonthlyIncidents=incident_freq,
            MTTRTrendSlope=mttr_trend, UptimeTrendSlope=uptime_trend, LatestUtilizationPct=latest_util,
        ))
    df = pd.DataFrame(combos)

    def norm(s, invert=False):
        s = s.astype(float)
        rng = (s.max() - s.min()) or 1
        n = (s - s.min()) / rng
        return 1 - n if invert else n

    df["f_incident_freq"] = norm(df["AvgMonthlyIncidents"])
    df["f_mttr_worsening"] = norm(df["MTTRTrendSlope"].clip(lower=0))
    df["f_uptime_declining"] = norm((-df["UptimeTrendSlope"]).clip(lower=0))
    df["f_high_utilization"] = norm(df["LatestUtilizationPct"])

    weights = dict(f_incident_freq=0.35, f_high_utilization=0.28, f_mttr_worsening=0.22, f_uptime_declining=0.15)
    raw_score = sum(df[f] * w for f, w in weights.items()) * 100
    lo, hi = raw_score.min(), raw_score.max()
    df["NetworkRiskScore"] = ((raw_score - lo) / (hi - lo) * 100).round(1)

    q50, q80, q93 = df["NetworkRiskScore"].quantile([0.50, 0.80, 0.93])

    def band(score):
        if score >= q93:
            return "Critical"
        elif score >= q80:
            return "High"
        elif score >= q50:
            return "Medium"
        return "Low"

    df["RiskBand"] = df["NetworkRiskScore"].apply(band)

    label_map = {
        "f_incident_freq": "High incident frequency", "f_mttr_worsening": "MTTR trending worse",
        "f_uptime_declining": "Uptime trending down", "f_high_utilization": "High capacity utilization",
    }
    top_drivers = []
    for _, row in df.iterrows():
        contribs = {f: row[f] * w for f, w in weights.items()}
        top2 = sorted(contribs.items(), key=lambda kv: kv[1], reverse=True)[:2]
        top_drivers.append(" & ".join(label_map[k] for k, _ in top2))
    df["TopRiskDrivers"] = top_drivers

    out_cols = ["Region", "NetworkType", "AvgMonthlyIncidents", "LatestUtilizationPct",
                "NetworkRiskScore", "RiskBand", "TopRiskDrivers"]
    return df[out_cols].sort_values("NetworkRiskScore", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    import os
    base = os.path.dirname(os.path.abspath(__file__)) + os.sep

    incidents = pd.read_csv(base + "_cache_incidents.csv")
    orders = pd.read_csv(base + "_cache_orders.csv")
    capacity = pd.read_csv(base + "_cache_capacity.csv")
    uptime = pd.read_csv(base + "_cache_uptime.csv")

    incident_fc = forecast_incident_volume(incidents)
    demand_fc, slope = forecast_service_demand(orders)
    capacity_fc = forecast_capacity_exhaustion(capacity)
    network_risk = score_network_risk(incidents, uptime, capacity)

    incident_fc.to_csv(base + "_cache_incident_forecast.csv", index=False)
    demand_fc.to_csv(base + "_cache_demand_forecast.csv", index=False)
    capacity_fc.to_csv(base + "_cache_capacity_forecast.csv", index=False)
    network_risk.to_csv(base + "_cache_network_risk.csv", index=False)

    print("Forecasting complete.")
    print(f"  Service demand trend slope: {slope:+.1f} orders/month")
    print(f"  12-month forecast incident count (last month): {incident_fc['ForecastIncidentCount'].iloc[-1]:.0f}")
    print(f"  12-month forecast order count (last month): {demand_fc['ForecastOrderCount_Blended'].iloc[-1]:.0f}")
    print(f"  Regions/network types approaching capacity (<12mo): {(capacity_fc['MonthsToExhaustion'].dropna() < 12).sum()}")
    print(f"  Network risk bands: {network_risk['RiskBand'].value_counts().to_dict()}")
