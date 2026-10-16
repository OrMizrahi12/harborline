Review this pull request's diff. Report only the problems listed under "Report".

Report:
- bug: code that crashes, or gives a wrong result, on data this project really has
- convention: code that breaks a rule in CLAUDE.md or in docs/conventions/
- security: a secret in the code, or outside input that reaches a shell, a file path or a refund

Skip, even when you notice it:
- naming, formatting, docstrings, comments and code style
- refactors, performance ideas and "consider" suggestions
- anything you can't tie to one line of the diff

Severity:
- high: wrong money or wrong dates reach a customer or a report. Example: a refund computed by hand instead of with policy.check_refund.
- medium: a crash on real data. Example: datetime.fromisoformat(order["promised_by"]) on an order whose dates are Unix seconds.
- low: wrong only on rare inputs, and no customer sees it.
