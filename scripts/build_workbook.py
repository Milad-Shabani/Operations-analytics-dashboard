"""
TelNova Communications - Operations Analytics
Excel Workbook Builder
=================================================
Assembles the final, formatted, formula-driven .xlsx deliverable from the
cached synthetic datasets produced by generate_ops_data.py and
forecast_engine.py.

Author: Milad Shabani
"""

import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter
from openpyxl.chart import LineChart, BarChart, Reference
from openpyxl.formatting.rule import ColorScaleRule
from datetime import datetime, date
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE = SCRIPT_DIR + os.sep
OUT_PATH = os.path.join(PROJECT_ROOT, "data", "Operations_Analytics_Workbook.xlsx")

NAVY = "1B2A4A"
TEAL = "0E7C7B"
WHITE = "FFFFFF"

HEADER_FONT = Font(name="Calibri", size=11, bold=True, color=WHITE)
HEADER_FILL = PatternFill("solid", fgColor=NAVY)
TITLE_FONT = Font(name="Calibri", size=16, bold=True, color=NAVY)
SUBTITLE_FONT = Font(name="Calibri", size=10, italic=True, color="666666")
BODY_FONT = Font(name="Calibri", size=10)
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def style_header_row(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER


def autosize(ws, df, max_width=38):
    for i, col in enumerate(df.columns, start=1):
        series_len = df[col].apply(lambda x: len(str(x))).max() if len(df) else 0
        width = min(max(len(str(col)) + 2, (series_len or 0) + 2), max_width)
        ws.column_dimensions[get_column_letter(i)].width = width


def write_table(ws, df, start_row, table_name, style="TableStyleMedium9"):
    for j, col in enumerate(df.columns, start=1):
        ws.cell(row=start_row, column=j, value=col)
    for i, (_, row) in enumerate(df.iterrows(), start=start_row + 1):
        for j, col in enumerate(df.columns, start=1):
            val = row[col]
            if isinstance(val, (np.integer,)):
                val = int(val)
            elif isinstance(val, (np.floating,)):
                val = float(val)
            elif pd.isna(val):
                val = None
            elif isinstance(val, (pd.Timestamp, datetime)):
                val = val.date()
            ws.cell(row=i, column=j, value=val)

    n_rows = len(df)
    n_cols = len(df.columns)
    last_col_letter = get_column_letter(n_cols)
    last_row = start_row + n_rows
    ref = f"{get_column_letter(1)}{start_row}:{last_col_letter}{last_row}"
    table = Table(displayName=table_name, ref=ref)
    table.tableStyleInfo = TableStyleInfo(name=style, showRowStripes=True, showFirstColumn=False)
    ws.add_table(table)
    autosize(ws, df)
    return start_row, last_row, n_cols


def add_cover_note(ws, title, subtitle, ncols=6):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    c = ws.cell(row=1, column=1, value=title)
    c.font = TITLE_FONT
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
    c2 = ws.cell(row=2, column=1, value=subtitle)
    c2.font = SUBTITLE_FONT
    ws.row_dimensions[1].height = 26
    ws.row_dimensions[3].height = 6


def main():
    uptime = pd.read_csv(BASE + "_cache_uptime.csv")
    incidents = pd.read_csv(BASE + "_cache_incidents.csv")
    orders = pd.read_csv(BASE + "_cache_orders.csv")
    callcenter = pd.read_csv(BASE + "_cache_callcenter.csv")
    capacity = pd.read_csv(BASE + "_cache_capacity.csv")
    maintenance = pd.read_csv(BASE + "_cache_maintenance.csv")
    inventory = pd.read_csv(BASE + "_cache_inventory.csv")
    incident_fc = pd.read_csv(BASE + "_cache_incident_forecast.csv")
    demand_fc = pd.read_csv(BASE + "_cache_demand_forecast.csv")
    capacity_fc = pd.read_csv(BASE + "_cache_capacity_forecast.csv")
    network_risk = pd.read_csv(BASE + "_cache_network_risk.csv")

    wb = Workbook()
    wb.remove(wb.active)

    # ------------------------------------------------------------------
    # README
    # ------------------------------------------------------------------
    ws = wb.create_sheet("README")
    ws.sheet_view.showGridLines = False
    add_cover_note(ws, "TelNova Communications - Operations Analytics",
                    "Synthetic dataset generated for portfolio / demonstration purposes  |  Author: Milad Shabani", ncols=2)
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 110

    rows = [
        ("Company profile", "Fictional converged telecom/ISP operator (same company as the companion HR and Finance Analytics projects). ~1,047,500 subscribers across 4 regions and 3 network types."),
        ("Data status", "100% synthetically generated with a fixed random seed (reproducible). No real company's operations are represented."),
        ("Sheets - raw data", "Network_Uptime, Incidents, Field_Service_Orders, Call_Center_Ops, Network_Capacity, Maintenance_Log, Inventory_CPE -- native Excel Tables, safe to filter/pivot directly."),
        ("Sheets - forecast", "Incident_Forecast, Demand_Forecast, Capacity_Exhaustion: 12-month forward-looking operations plan. Methodology documented on each sheet."),
        ("Sheets - risk model", "Network_Risk: an explainable weighted-factor model scoring every region/network-type combination 0-100 on operational risk. Methodology documented on the sheet."),
        ("Sheets - KPIs", "KPI_Dashboard: headline metrics computed with live AVERAGE / SUMIFS / COUNTIFS formulas referencing the raw data tables."),
        ("Companion projects", "See also: HR Analytics Dashboard and Finance Analytics Dashboard -- independent repos covering the same fictional company's people and financial data."),
        ("Companion dashboard", "dashboard/index.html reads this workbook's data (embedded at build time) to render an interactive operations dashboard -- see project README.md."),
    ]
    r = 4
    for label, text in rows:
        ws.cell(row=r, column=1, value=label).font = Font(bold=True, size=10, color=NAVY)
        cell = ws.cell(row=r, column=2, value=text)
        cell.font = BODY_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 32
        r += 1

    # ------------------------------------------------------------------
    # Network_Uptime
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Network_Uptime")
    start, last_row, ncols = write_table(ws, uptime, 1, "tbl_Uptime")
    style_header_row(ws, 1, ncols)
    ws.freeze_panes = "A2"

    # ------------------------------------------------------------------
    # Incidents
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Incidents")
    incidents_out = incidents.drop(columns=["DateTime"]) if "DateTime" in incidents.columns else incidents
    start, last_row, ncols = write_table(ws, incidents_out, 1, "tbl_Incidents")
    style_header_row(ws, 1, ncols)
    ws.freeze_panes = "A2"

    # ------------------------------------------------------------------
    # Field_Service_Orders
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Field_Service_Orders")
    start, last_row, ncols = write_table(ws, orders, 1, "tbl_Orders")
    style_header_row(ws, 1, ncols)
    ws.freeze_panes = "A2"

    # ------------------------------------------------------------------
    # Call_Center_Ops
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Call_Center_Ops")
    start, last_row, ncols = write_table(ws, callcenter, 1, "tbl_CallCenter")
    style_header_row(ws, 1, ncols)
    ws.freeze_panes = "A2"

    chart = LineChart()
    chart.title = "Call Volume & CSAT (48 months)"
    chart.style = 2
    vol_col = callcenter.columns.get_loc("CallVolume") + 1
    data = Reference(ws, min_col=vol_col, max_col=vol_col, min_row=1, max_row=last_row)
    cats = Reference(ws, min_col=1, min_row=2, max_row=last_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.width, chart.height = 24, 9
    ws.add_chart(chart, f"A{last_row + 3}")

    # ------------------------------------------------------------------
    # Network_Capacity
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Network_Capacity")
    start, last_row, ncols = write_table(ws, capacity, 1, "tbl_Capacity")
    style_header_row(ws, 1, ncols)
    ws.freeze_panes = "A2"

    # ------------------------------------------------------------------
    # Maintenance_Log
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Maintenance_Log")
    start, last_row, ncols = write_table(ws, maintenance, 1, "tbl_Maintenance")
    style_header_row(ws, 1, ncols)
    ws.freeze_panes = "A2"

    # ------------------------------------------------------------------
    # Inventory_CPE
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Inventory_CPE")
    start, last_row, ncols = write_table(ws, inventory, 1, "tbl_Inventory")
    style_header_row(ws, 1, ncols)
    ws.freeze_panes = "A2"

    # ------------------------------------------------------------------
    # Incident_Forecast
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Incident_Forecast")
    add_cover_note(ws, "12-Month Incident Volume Forecast", "", ncols=4)
    ws.cell(row=3, column=1, value="Methodology: Holt's linear (double) exponential smoothing (alpha=0.35, beta=0.25) fitted on 24 months of monthly incident counts, projected forward.").font = SUBTITLE_FONT
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=6)
    start, last_row, ncols = write_table(ws, incident_fc, 5, "tbl_IncidentForecast")
    style_header_row(ws, 5, ncols)

    fc_chart = LineChart()
    fc_chart.title = "Forecast Incident Volume (next 12 months)"
    data = Reference(ws, min_col=2, max_col=2, min_row=5, max_row=last_row)
    cats = Reference(ws, min_col=1, min_row=6, max_row=last_row)
    fc_chart.add_data(data, titles_from_data=True)
    fc_chart.set_categories(cats)
    fc_chart.width, fc_chart.height = 22, 9
    ws.add_chart(fc_chart, f"A{last_row + 3}")

    # ------------------------------------------------------------------
    # Demand_Forecast
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Demand_Forecast")
    add_cover_note(ws, "12-Month Field Service Demand Forecast", "", ncols=4)
    ws.cell(row=3, column=1, value="Methodology: 50% linear-trend regression on last 18 months of order volume, blended 50% with a stated 7% annual growth target (aligned to subscriber growth).").font = SUBTITLE_FONT
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=6)
    start, last_row, ncols = write_table(ws, demand_fc, 5, "tbl_DemandForecast")
    style_header_row(ws, 5, ncols)

    # ------------------------------------------------------------------
    # Capacity_Exhaustion
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Capacity_Exhaustion")
    add_cover_note(ws, "Network Capacity Exhaustion Projection", "", ncols=6)
    ws.cell(row=3, column=1, value="Methodology: linear-trend regression on the last 18 months of utilization % per region/network-type, projected forward to estimate months until crossing a 90% capacity threshold.").font = SUBTITLE_FONT
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=6)
    start, last_row, ncols = write_table(ws, capacity_fc, 5, "tbl_CapacityExhaustion")
    style_header_row(ws, 5, ncols)

    # ------------------------------------------------------------------
    # Network_Risk
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Network_Risk")
    add_cover_note(ws, "Region / Network-Type Risk Scoring", "", ncols=6)
    ws.cell(row=3, column=1, value="Methodology: explainable weighted-factor model (0-100). Weights: Incident frequency 35%, Capacity utilization 28%, MTTR trend 22%, Uptime trend 15%. Min-max scaled; bands set from this population's 50th/80th/93rd percentiles.").font = SUBTITLE_FONT
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=6)
    start, last_row, ncols = write_table(ws, network_risk, 5, "tbl_NetworkRisk")
    style_header_row(ws, 5, ncols)

    score_col_idx = network_risk.columns.get_loc("NetworkRiskScore") + 1
    score_col_letter = get_column_letter(score_col_idx)
    color_rule = ColorScaleRule(start_type="min", start_color="63BE7B", mid_type="percentile", mid_value=50,
                                 mid_color="FFEB84", end_type="max", end_color="F8696B")
    ws.conditional_formatting.add(f"{score_col_letter}6:{score_col_letter}{last_row}", color_rule)

    # ------------------------------------------------------------------
    # KPI_Dashboard (live formulas)
    # ------------------------------------------------------------------
    ws = wb.create_sheet("KPI_Dashboard", 0)
    ws.sheet_view.showGridLines = False
    add_cover_note(ws, "TelNova Communications - Operations KPI Dashboard (Live)", "All figures below are Excel formulas referencing tbl_Uptime / tbl_Incidents / tbl_Orders / tbl_CallCenter / tbl_Capacity -- change the raw data and these recalculate automatically.", ncols=4)

    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 4
    ws.column_dimensions["D"].width = 42
    ws.column_dimensions["E"].width = 18

    n_cc = len(callcenter)
    kpis_left = [
        ("Avg. Network Uptime (all types)", "=AVERAGE(tbl_Uptime[UptimePct])", "0.000%"),
        ("Overall SLA Compliance Rate", '=COUNTIF(tbl_Uptime[SLA_Met],"Yes")/COUNTA(tbl_Uptime[SLA_Met])', "0.0%"),
        ("Total Incidents (24mo)", "=COUNTA(tbl_Incidents[IncidentID])", "0"),
        ("Avg. MTTR, All Severities (minutes)", "=AVERAGE(tbl_Incidents[ResolutionTimeMinutes])", "0.0"),
        ("Critical (P1) Incidents (24mo)", '=COUNTIF(tbl_Incidents[Severity],"P1 - Critical")', "0"),
        ("Avg. Detection Time (minutes)", "=AVERAGE(tbl_Incidents[DetectionTimeMinutes])", "0.0"),
        ("Total Field Service Orders (24mo)", "=COUNTA(tbl_Orders[OrderID])", "0"),
        ("First-Time-Fix Rate", '=COUNTIF(tbl_Orders[FirstTimeFix],"Yes")/COUNTA(tbl_Orders[FirstTimeFix])', "0.0%"),
        ("Avg. Service Cycle Time (days)", "=AVERAGE(tbl_Orders[CycleTimeDays])", "0.00"),
    ]

    kpis_right = [
        ("Latest Monthly Call Volume", f"=INDEX(tbl_CallCenter[CallVolume],{n_cc})", "#,##0"),
        ("Avg. Handle Time (minutes)", f"=INDEX(tbl_CallCenter[AvgHandleTimeMinutes],{n_cc})", "0.00"),
        ("First Contact Resolution Rate", f"=INDEX(tbl_CallCenter[FirstContactResolutionPct],{n_cc})", "0.0%"),
        ("Latest CSAT Score", f"=INDEX(tbl_CallCenter[CSAT_Score],{n_cc})", "0.00"),
        ("Latest Ticket Backlog", f"=INDEX(tbl_CallCenter[TicketBacklog],{n_cc})", "#,##0"),
        ("Avg. Network Capacity Utilization", "=AVERAGE(tbl_Capacity[UtilizationPct])", "0.0%"),
        ("Preventive Maintenance Share", '=COUNTIF(tbl_Maintenance[MaintenanceType],"Preventive")/COUNTA(tbl_Maintenance[MaintenanceType])', "0.0%"),
        ("Total Maintenance Cost (24mo)", "=SUM(tbl_Maintenance[CostUSD])", '"$"#,##0'),
        ("CPE Locations Flagged Stockout", '=COUNTIF(tbl_Inventory[StockoutFlag],"Yes")', "0"),
    ]

    r0 = 5
    ws.cell(row=r0, column=1, value="NETWORK RELIABILITY & FIELD SERVICE").font = Font(bold=True, size=12, color=TEAL)
    ws.cell(row=r0, column=4, value="CUSTOMER SUPPORT, CAPACITY & ASSETS").font = Font(bold=True, size=12, color=TEAL)
    for i, (label, formula, fmt) in enumerate(kpis_left):
        rr = r0 + 1 + i
        ws.cell(row=rr, column=1, value=label).font = BODY_FONT
        c = ws.cell(row=rr, column=2, value=formula)
        c.number_format = fmt
        c.font = Font(bold=True, size=11, color=NAVY)
    for i, (label, formula, fmt) in enumerate(kpis_right):
        rr = r0 + 1 + i
        ws.cell(row=rr, column=4, value=label).font = BODY_FONT
        c = ws.cell(row=rr, column=5, value=formula)
        c.number_format = fmt
        c.font = Font(bold=True, size=11, color=NAVY)

    note_row = r0 + max(len(kpis_left), len(kpis_right)) + 3
    ws.cell(row=note_row, column=1, value="Forecast, capacity-exhaustion and network-risk figures live on their own sheets (Incident_Forecast, Demand_Forecast, Capacity_Exhaustion, Network_Risk) because they are statistical model output, not raw-data formulas.").font = SUBTITLE_FONT
    ws.merge_cells(start_row=note_row, start_column=1, end_row=note_row, end_column=5)

    order = ["KPI_Dashboard", "README", "Network_Uptime", "Incidents", "Field_Service_Orders", "Call_Center_Ops",
             "Network_Capacity", "Maintenance_Log", "Inventory_CPE",
             "Incident_Forecast", "Demand_Forecast", "Capacity_Exhaustion", "Network_Risk"]
    wb._sheets = [wb[name] for name in order]
    for name in order:
        wb[name].sheet_properties.tabColor = TEAL if name == "KPI_Dashboard" else NAVY

    wb.save(OUT_PATH)
    print(f"Workbook saved to {OUT_PATH}")


if __name__ == "__main__":
    main()
