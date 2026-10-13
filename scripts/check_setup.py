"""Check that this computer is ready for Harborline. Makes no API calls.

Run it from the repository folder:  python -m scripts.check_setup
"""

import sys
from importlib import metadata
from pathlib import Path

from harborline import data
from harborline.config import MODEL, ROOT_DIR

PACKAGES = ["anthropic", "python-dotenv", "pytest"]


def check_python():
    version = ".".join(str(n) for n in sys.version_info[:3])
    ok = sys.version_info >= (3, 12)
    return ok, f"Python {version}" + ("" if ok else " (this course uses 3.12 or newer)")


def check_package(name):
    try:
        return True, f"{name} {metadata.version(name)}"
    except metadata.PackageNotFoundError:
        return False, f"{name} is not installed (run: pip install -r requirements.txt)"


def check_env_file():
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return None, ".env not found yet (copy .env.example to .env; the API lessons need it)"
    from dotenv import dotenv_values

    has_key = bool(dotenv_values(env_path).get("ANTHROPIC_API_KEY"))
    # Never print the key itself: only whether it is there.
    if has_key:
        return True, ".env found, ANTHROPIC_API_KEY is set"
    return None, ".env found, but ANTHROPIC_API_KEY is empty"


def check_data():
    counts = (
        f"{len(data.customers())} customers, {len(data.orders())} orders, "
        f"{len(data.tickets())} tickets, {len(data.invoice_labels())} invoices, "
        f"{len(data.research_sources())} research sources"
    )
    return True, counts


def main():
    print("Harborline setup check")
    results = [check_python()]
    results += [check_package(name) for name in PACKAGES]
    results += [check_env_file(), check_data()]
    for ok, message in results:
        mark = {True: "ok  ", False: "FAIL", None: "note"}[ok]
        print(f"  [{mark}] {message}")
    print(f"  Default model: {MODEL}")

    if any(ok is False for ok, _ in results):
        print("Fix the FAIL lines above, then run this again.")
        return 1
    print("All set.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
