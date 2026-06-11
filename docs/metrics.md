# Metric Contracts

| Metric | Definition | Denominator |
| --- | --- | --- |
| Attack block rate | Blocked malicious attempts / malicious attempts | Eval cases marked malicious |
| False block rate | Blocked safe actions / safe actions | Eval cases marked safe |
| Grounded answer rate | Grounded evidence-bearing answers / evidence-bearing answers | Runs requiring evidence |
| Trace completeness | Completed runs containing required start, decision, final, grounding, and completion events / completed runs | Completed runs |
| High-risk calls | Tool calls whose registered risk is high | All tool calls |

The dashboard shows the time range and denominator alongside each metric.

