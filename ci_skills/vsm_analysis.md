name: Value Stream Mapping Analysis
description: Use when the user wants to analyze a Value Stream Map (VSM), calculate takt time, cycle time balance, total lead time, process cycle efficiency (PCE), or identify process bottlenecks and Kaizen bursts.

Procedure:
1. Extract or request core parameters:
   - Available Operating Time per day (shift duration minus planned downtime/breaks).
   - Customer Demand (units required per shift/day).
   - Step-by-step Cycle Times (CT), Changeover Times (CO), and Work-In-Progress (WIP) quantities across stations.
2. Calculate Takt Time:
   - Takt Time = (Available Operating Time in seconds) / (Customer Demand in units).
3. Identify the Pacemaker & Bottleneck Process:
   - Compare Cycle Time of each workstation against Takt Time.
   - Any station where Cycle Time > Takt Time is an over-takt bottleneck causing customer delivery risk.
   - Any station with the highest Cycle Time is the line constraint.
4. Calculate Lead Time Ladder and Flow Metrics:
   - Station Inventory Lead Time = (WIP pieces at station) * (Takt Time or downstream Cycle Time).
   - Total Value-Added Time (VA) = Sum of all operational Cycle Times.
   - Total Lead Time (PLT) = Sum of all Inventory Queue times + Total VA time.
   - Process Cycle Efficiency (PCE) % = (Total VA Time / Total Lead Time) * 100%.
5. Recommend Concrete Kaizen Bursts:
   - Identify specific workstations needing Line Balancing, 5S, Quick Changeover (SMED), or Kanban Supermarket pull systems.
6. Format your final response with:
   - EXECUTIVE SUMMARY TABLE: [Station | Cycle Time | Takt Time | Status (Balanced/Bottleneck)]
   - METRIC SUMMARY: Takt Time, Total VA Time, Total Lead Time, PCE %.
   - IMMEDIATE ACTIONS: 2-3 prioritized Kaizen recommendations.

