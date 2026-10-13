"""The errors Harborline's backend can raise.

Each kind of failure has its own class, so the code that calls the backend
can tell them apart: try again later, fix the request, or stop and explain.
"""


class BackendError(Exception):
    """Base class for every backend failure."""

    kind = "backend"
    retryable = False


class NotFound(BackendError):
    """The customer, order or item does not exist."""

    kind = "not_found"


class InvalidRequest(BackendError):
    """The request itself is malformed (bad ID format, missing field...)."""

    kind = "validation"


class PermissionDenied(BackendError):
    """The caller may not do this (wrong customer, account on hold...)."""

    kind = "permission"


class PolicyViolation(BackendError):
    """The request is valid, but the refund policy does not allow it."""

    kind = "business"


class ServiceUnavailable(BackendError):
    """A downstream system timed out. Trying again later may work."""

    kind = "transient"
    retryable = True
