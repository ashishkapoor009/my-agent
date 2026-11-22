name: Poka-Yoke and Process FMEA Risk Assessment
description: Use when the user wants to conduct Failure Mode and Effects Analysis (FMEA), calculate Risk Priority Number (RPN), or design mistake-proofing (Poka-Yoke) solutions.

Procedure:
1. Define the Process Step and Potential Failure Modes:
   - Identify what can go wrong at this specific step (e.g., missing screw, inverted connector, wrong component loaded).
2. Assess Rating Factors (1-10 Scale):
   - Severity (S): How critical is the effect on the customer/downstream operation? (1 = Noticeable minor flaw, 10 = Hazardous without warning).
   - Occurrence (O): How frequently does the cause happen? (1 = Extremely rare < 1 in 1M, 10 = Very high > 1 in 10).
   - Detection (D): How likely will current controls catch the defect before reaching the customer? (1 = Almost certain detection, 10 = Cannot be detected / no control).
3. Compute Risk Priority Number (RPN):
   - RPN = Severity (S) * Occurrence (O) * Detection (D). (Scale: 1 to 1000).
   - Trigger threshold: Any RPN > 100, or any Severity >= 9 requires immediate corrective action.
4. Prescribe Poka-Yoke (Mistake-Proofing) Level:
   - Level 1 - Warning/Detection: Buzzer, flashing light, warning screen (operator can still bypass).
   - Level 2 - Interlock/Control: Machine will not cycle if part is misaligned or missing (stops the line).
   - Level 3 - Contact/Design Elimination: Physical impossibility of incorrect assembly (asymmetrical pins, keyed connectors).
5. Post-Action RPN Re-evaluation:
   - Calculate projected Severity', Occurrence', Detection' and new RPN' after mistake-proofing.
6. Format your final response with:
   - FMEA RISK MATRIX TABLE: [Process Step | Failure Mode | Cause | Current S-O-D | RPN]
   - POKA-YOKE MISTAKE-PROOFING ARCHITECTURE (Level 1, 2, or 3 recommendation)
   - PROJECTED POST-KAIZEN RPN & RESIDUAL RISK

