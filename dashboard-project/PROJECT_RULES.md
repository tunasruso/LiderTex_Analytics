# Business Rules: LiderTex Analytics Dashboard

## Scope: Trading House only (Торговый Дом ЛидерТекс)
- **Sales Facts**: Revenue and Gross Profit calculations must ONLY include data from departments/teams explicitly listed in the regional mapping file (`TerritoriesReletionsRegions.xlsx`).
- **Team Mapping**: These teams are synced to the PostgreSQL table `mart.territory_teams_mapping`. 
- **Exclusions**: 
    - **Team 230**, **Corporate Sales (КОРПОРАТ)**, and **Sales Support (ПОДДЕРЖК)** are NOT part of the Trading House and MUST be excluded from the report.
    - If a sales record's team is not found in the mapping or fallback heuristics (strictly 214/Moscow or similar direct regional matches), it must be ignored.

## Calculation Logic: Daily Target (Catch-Up)
- **Formula**: `Daily_Target = (Month_Plan_Total - Fact_YTD) / Remaining_Working_Days`
- **Negative Targets**: If the Month Plan is already exceeded (`Fact_YTD > Month_Plan_Total`), the logic should allow a negative target (surplus) instead of zeroing it out, to reflect the actual business performance state.
- **Excluded Categories**: 
    - **Bags (Bugs)**: While monitored, the revenue from the Bags category is EXCLUDED from the regional "Revenue" total in the Daily Plan view to focus on core production and resale targets.
    - **China/Resale**: These categories are handled as separate components but included in the overall plan total where specified by the user.

## Data Sources
- **Plans**: Sourced from Excel files (`Plans_2026.xlsx`) and stored in Postgres `plans.plans`.
- **Facts**: Extracted from MySQL CRM into Postgres `raw` schema.
- **Timezone**: All date-based filtering and display must use `Europe/Moscow` (UTC+3) to ensure consistency between Vercel and local environments.
