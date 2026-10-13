"""Settings shared by every Harborline system.

Change a value here, not inside the code that uses it.
"""

from datetime import date
from pathlib import Path

# The model every API call uses unless a lesson says otherwise.
# Start with the cheapest model that does the job; step up only on evidence.
MODEL = "claude-haiku-5-5"

# Upper limit on the tokens one reply may use (thinking included).
MAX_TOKENS = 1024

# Harborline's "today". The data is fixed, so the date is fixed too:
# return windows and order ages are measured from this day.
BUSINESS_DATE = date(2026, 10, 15)

# Refunds above this amount (in US dollars) need a support lead's approval.
REFUND_APPROVAL_LIMIT = 500.00

# Where the synthetic data lives.
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
