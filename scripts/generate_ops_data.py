"""
TelNova Communications - Operations Analytics
Synthetic Operations Data Generation Engine
=================================================
Generates a realistic, internally-consistent operations dataset for the
same fictional ISP/telecom operator used in the companion HR Analytics
and Finance Analytics projects (~1,047,500 subscribers, 4 regions).

Covers:
    - Network uptime & SLA compliance by region/network type (48 months)
    - A detailed incident/outage log (24 months) with severity, root
      cause, detection & resolution time (MTTR)
    - Field service orders: installs, repairs, upgrades -- first-time-fix
      rate, truck rolls, backlog (24 months)
    - Call center operations: volume, handle time, first-contact
      resolution, CSAT, backlog (48 months)
    - Network capacity utilization by region/network type (48 months)
    - A maintenance log: preventive vs. corrective work orders (24 months)
    - CPE inventory levels (routers, ONTs, set-top boxes, modems) by
      warehouse region (24 months)

All figures are FICTIONAL and generated with a fixed random seed for full
reproducibility. No real company's operations are represented.

Author: Milad Shabani
Project: TelNova Operations Analytics
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

# ----------------------------------------------------------------------
# 0. GLOBAL CONFIG
# ----------------------------------------------------------------------
SEED = 3391
np.random.seed(SEED)
random.seed(SEED)

TODAY = datetime(2026, 9, 1)
HISTORY_MONTHS = 48
INCIDENT_HISTORY_MONTHS = 24
TOTAL_SUBSCRIBERS = 1_047_500

REGIONS = {
    "Capital Region": dict(share=0.38, incident_mult=0.85),
    "North Region":   dict(share=0.24, incident_mult=1.10),
    "South Region":   dict(share=0.22, incident_mult=1.20),
    "East Region":    dict(share=0.16, incident_mult=1.35),
}
NETWORK_TYPES = ["Fiber Access", "Mobile/Cellular", "Core & Backbone"]

SEVERITY_LEVELS = {
    # severity: (share_of_incidents, base_mttr_minutes, base_detect_minutes, avg_affected_subs)
    "P1 - Critical": dict(share=0.05, mttr=210, detect=6, affected=8500),
    "P2 - Major":    dict(share=0.18, mttr=95,  detect=12, affected=1900),
    "P3 - Minor":    dict(share=0.42, mttr=48,  detect=22, affected=280),
    "P4 - Low":      dict(share=0.35, mttr=22,  detect=35, affected=35),
}

ROOT_CAUSES = [
    ("Fiber Cut", 0.20), ("Hardware Failure", 0.18), ("Power Outage", 0.14),
    ("Configuration Error", 0.12), ("Software/Firmware Bug", 0.10), ("Weather Event", 0.09),
    ("Capacity Exhaustion", 0.07), ("Third-Party Circuit Failure", 0.05),
    ("Planned Maintenance Overrun", 0.03), ("Unknown / Under Investigation", 0.02),
]

ORDER_TYPES = {
    "New Installation": dict(share=0.42, base_days=4.5, fix_rate=0.86),
    "Repair / Trouble Ticket": dict(share=0.38, base_days=1.8, fix_rate=0.78),
    "Upgrade / Plan Change": dict(share=0.14, base_days=3.0, fix_rate=0.92),
    "Disconnect / Downgrade": dict(share=0.06, base_days=2.2, fix_rate=0.95),
}

MAINTENANCE_TYPES = ["Preventive", "Corrective"]

EQUIPMENT_TYPES = ["ONT / Fiber Terminal", "Wi-Fi Router", "Cable Modem", "Set-Top Box", "Mobile Hotspot Device"]


def month_range(n_months, end_month=TODAY):
    return pd.date_range(end=end_month, periods=n_months, freq="MS")


# ----------------------------------------------------------------------
# 1. NETWORK UPTIME & SLA COMPLIANCE
# ----------------------------------------------------------------------
def generate_network_uptime():
    months = month_range(HISTORY_MONTHS)
    records = []
    for region, rcfg in REGIONS.items():
        for ntype in NETWORK_TYPES:
            base_uptime = {"Fiber Access": 99.92, "Mobile/Cellular": 99.80, "Core & Backbone": 99.97}[ntype]
            sla_target = {"Fiber Access": 99.85, "Mobile/Cellular": 99.70, "Core & Backbone": 99.90}[ntype]
            for i, m in enumerate(months):
                drift = np.random.normal(0, 0.03) - (rcfg["incident_mult"] - 1) * 0.015
                uptime = np.clip(base_uptime + drift + np.random.normal(0, 0.025), 98.5, 100.0)
                downtime_minutes = round((1 - uptime / 100) * 30.44 * 24 * 60, 1)
                records.append(dict(
                    Month=m.date(), Region=region, NetworkType=ntype,
                    UptimePct=round(uptime, 4), DowntimeMinutes=downtime_minutes,
                    SLA_TargetPct=sla_target, SLA_Met="Yes" if uptime >= sla_target else "No",
                ))
    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# 2. INCIDENT / OUTAGE LOG
# ----------------------------------------------------------------------
def generate_incidents():
    months = month_range(INCIDENT_HISTORY_MONTHS)
    records = []
    incident_id = 20001

    base_incidents_per_month = 145  # company-wide baseline
    for i, m in enumerate(months):
        # slight declining trend (network reliability improving over time) with noise
        month_total = max(60, int(np.random.normal(base_incidents_per_month * (1 - i * 0.006), 14)))
        for _ in range(month_total):
            region = random.choices(list(REGIONS.keys()), weights=[r["share"] * r["incident_mult"] for r in REGIONS.values()], k=1)[0]
            ntype = random.choices(NETWORK_TYPES, weights=[0.45, 0.40, 0.15], k=1)[0]
            severity = random.choices(list(SEVERITY_LEVELS.keys()), weights=[s["share"] for s in SEVERITY_LEVELS.values()], k=1)[0]
            scfg = SEVERITY_LEVELS[severity]
            root_cause = random.choices([c[0] for c in ROOT_CAUSES], weights=[c[1] for c in ROOT_CAUSES], k=1)[0]

            day_offset = random.randint(0, 27)
            incident_date = m + timedelta(days=day_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59))

            detect_minutes = max(1, round(np.random.normal(scfg["detect"], scfg["detect"] * 0.35), 1))
            mttr_minutes = max(5, round(np.random.normal(scfg["mttr"], scfg["mttr"] * 0.40), 1))
            affected = max(1, int(np.random.normal(scfg["affected"], scfg["affected"] * 0.35)))

            records.append(dict(
                IncidentID=f"INC-{incident_id}", DateTime=incident_date, Month=m.date(),
                Region=region, NetworkType=ntype, Severity=severity, RootCause=root_cause,
                DetectionTimeMinutes=detect_minutes, ResolutionTimeMinutes=mttr_minutes,
                AffectedSubscribers=affected, Status="Resolved",
            ))
            incident_id += 1
    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# 3. FIELD SERVICE ORDERS
# ----------------------------------------------------------------------
def generate_field_service_orders():
    months = month_range(INCIDENT_HISTORY_MONTHS)
    records = []
    order_id = 500001

    base_orders_per_month = 3400
    for i, m in enumerate(months):
        growth_factor = 1 + i * 0.006  # gradual order-volume growth, consistent with subscriber growth
        month_total = max(1800, int(np.random.normal(base_orders_per_month * growth_factor, 220)))
        for _ in range(month_total):
            order_type = random.choices(list(ORDER_TYPES.keys()), weights=[o["share"] for o in ORDER_TYPES.values()], k=1)[0]
            ocfg = ORDER_TYPES[order_type]
            region = random.choices(list(REGIONS.keys()), weights=[r["share"] for r in REGIONS.values()], k=1)[0]

            day_offset = random.randint(0, 27)
            scheduled_date = m + timedelta(days=day_offset)
            cycle_days = max(0.3, np.random.normal(ocfg["base_days"], ocfg["base_days"] * 0.35))
            completed_date = scheduled_date + timedelta(days=cycle_days)

            first_time_fix = "Yes" if random.random() < ocfg["fix_rate"] else "No"
            truck_roll = "Yes" if order_type in ("New Installation", "Repair / Trouble Ticket") else random.choice(["Yes", "No"])

            records.append(dict(
                OrderID=f"SO-{order_id}", Month=m.date(), OrderType=order_type, Region=region,
                ScheduledDate=scheduled_date.date(), CompletedDate=completed_date.date(),
                CycleTimeDays=round(cycle_days, 2), FirstTimeFix=first_time_fix, TruckRoll=truck_roll,
            ))
            order_id += 1
    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# 4. CALL CENTER OPERATIONS
# ----------------------------------------------------------------------
def generate_call_center_ops():
    months = month_range(HISTORY_MONTHS)
    records = []
    base_volume = 145_000  # monthly calls, company-wide (scales with subscriber base)
    for i, m in enumerate(months):
        growth = 1 + i * 0.004
        volume = max(60_000, int(np.random.normal(base_volume * growth, 6_000)))
        aht = max(2.5, np.random.normal(6.4 - i * 0.006, 0.35))  # AHT slowly improving (process efficiency)
        fcr = np.clip(np.random.normal(0.74 + i * 0.0015, 0.02), 0.55, 0.92)
        abandonment = np.clip(np.random.normal(0.055 - i * 0.0002, 0.012), 0.01, 0.12)
        csat = np.clip(np.random.normal(4.05 + i * 0.002, 0.12), 2.5, 5.0)
        backlog = max(0, int(np.random.normal(volume * 0.018, volume * 0.006)))

        records.append(dict(
            Month=m.date(), CallVolume=volume, AvgHandleTimeMinutes=round(aht, 2),
            FirstContactResolutionPct=round(fcr, 4), AbandonmentRatePct=round(abandonment, 4),
            CSAT_Score=round(csat, 2), TicketBacklog=backlog,
        ))
    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# 5. NETWORK CAPACITY UTILIZATION
# ----------------------------------------------------------------------
def generate_network_capacity():
    months = month_range(HISTORY_MONTHS)
    records = []
    base_capacity = {"Fiber Access": 1800, "Mobile/Cellular": 950, "Core & Backbone": 4200}  # Gbps
    for region, rcfg in REGIONS.items():
        for ntype in NETWORK_TYPES:
            total_capacity = base_capacity[ntype] * rcfg["share"] * np.random.uniform(0.9, 1.1)
            start_util = np.random.uniform(0.42, 0.55)
            for i, m in enumerate(months):
                util = np.clip(start_util + i * 0.0055 + np.random.normal(0, 0.015), 0.30, 0.97)
                used_capacity = total_capacity * util
                records.append(dict(
                    Month=m.date(), Region=region, NetworkType=ntype,
                    TotalCapacityGbps=round(total_capacity, 1), UsedCapacityGbps=round(used_capacity, 1),
                    UtilizationPct=round(util, 4),
                ))
    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# 6. MAINTENANCE LOG
# ----------------------------------------------------------------------
def generate_maintenance_log():
    months = month_range(INCIDENT_HISTORY_MONTHS)
    records = []
    maint_id = 90001
    for i, m in enumerate(months):
        n_preventive = int(np.random.normal(85, 12))
        n_corrective = int(np.random.normal(52, 10))
        for mtype, n in [("Preventive", n_preventive), ("Corrective", n_corrective)]:
            for _ in range(max(0, n)):
                region = random.choice(list(REGIONS.keys()))
                ntype = random.choice(NETWORK_TYPES)
                duration = max(0.5, np.random.normal(4.5 if mtype == "Preventive" else 7.2, 2.2))
                cost = duration * np.random.uniform(180, 340)
                outcome = "Completed" if random.random() < (0.97 if mtype == "Preventive" else 0.91) else "Escalated"
                day_offset = random.randint(0, 27)
                records.append(dict(
                    MaintenanceID=f"MNT-{maint_id}", Month=m.date(), Date=(m + timedelta(days=day_offset)).date(),
                    Region=region, NetworkType=ntype, MaintenanceType=mtype,
                    DurationHours=round(duration, 2), CostUSD=round(cost, 0), Outcome=outcome,
                ))
                maint_id += 1
    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# 7. CPE INVENTORY
# ----------------------------------------------------------------------
def generate_inventory():
    months = month_range(INCIDENT_HISTORY_MONTHS)
    records = []
    base_stock = {"ONT / Fiber Terminal": 9500, "Wi-Fi Router": 14200, "Cable Modem": 6800,
                  "Set-Top Box": 11000, "Mobile Hotspot Device": 3200}
    reorder_point = {k: int(v * 0.22) for k, v in base_stock.items()}
    lead_time = {"ONT / Fiber Terminal": 28, "Wi-Fi Router": 21, "Cable Modem": 24,
                 "Set-Top Box": 18, "Mobile Hotspot Device": 35}

    for region in REGIONS:
        for equip, base in base_stock.items():
            stock = base * REGIONS[region]["share"] * np.random.uniform(0.85, 1.15)
            for i, m in enumerate(months):
                consumption = stock * np.random.uniform(0.08, 0.16)
                replenishment = consumption * np.random.uniform(0.85, 1.25) if random.random() < 0.5 else 0
                stock = max(0, stock - consumption + replenishment)
                rp = reorder_point[equip] * REGIONS[region]["share"]
                records.append(dict(
                    Month=m.date(), Region=region, EquipmentType=equip,
                    StockLevel=int(round(stock)), ReorderPoint=int(round(rp)),
                    LeadTimeDays=lead_time[equip], StockoutFlag="Yes" if stock < rp * 0.4 else "No",
                ))
    return pd.DataFrame(records)


if __name__ == "__main__":
    import os
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    print("Generating TelNova Communications synthetic operations dataset...")

    uptime = generate_network_uptime()
    print(f"  Network uptime records: {len(uptime)}")

    incidents = generate_incidents()
    print(f"  Incident records: {len(incidents)}")

    orders = generate_field_service_orders()
    print(f"  Field service order records: {len(orders)}")

    callcenter = generate_call_center_ops()
    print(f"  Call center records: {len(callcenter)} months")

    capacity = generate_network_capacity()
    print(f"  Network capacity records: {len(capacity)}")

    maintenance = generate_maintenance_log()
    print(f"  Maintenance records: {len(maintenance)}")

    inventory = generate_inventory()
    print(f"  Inventory records: {len(inventory)}")

    uptime.to_csv(os.path.join(SCRIPT_DIR, "_cache_uptime.csv"), index=False)
    incidents.to_csv(os.path.join(SCRIPT_DIR, "_cache_incidents.csv"), index=False)
    orders.to_csv(os.path.join(SCRIPT_DIR, "_cache_orders.csv"), index=False)
    callcenter.to_csv(os.path.join(SCRIPT_DIR, "_cache_callcenter.csv"), index=False)
    capacity.to_csv(os.path.join(SCRIPT_DIR, "_cache_capacity.csv"), index=False)
    maintenance.to_csv(os.path.join(SCRIPT_DIR, "_cache_maintenance.csv"), index=False)
    inventory.to_csv(os.path.join(SCRIPT_DIR, "_cache_inventory.csv"), index=False)
    print("Cached intermediate CSVs. Ready for forecast_engine.py and build_workbook.py")
