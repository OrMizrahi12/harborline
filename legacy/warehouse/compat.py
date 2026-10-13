"""Old names, kept so that older scripts keep working. Don't use them in new code."""

from legacy.warehouse.codes import status_name

# The name the 2023 scripts used.
getStatus = status_name


def get_status_text(code):
    """Status as upper-case text. Accepts the code as a number or a string."""
    return status_name(int(code)).upper()
