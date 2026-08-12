"""Database helpers shared by the service layer."""

from collections.abc import Iterator
from contextlib import contextmanager

from django.db import IntegrityError, transaction

from mission_control.common.exceptions import ApplicationError


@contextmanager
def integrity_error_as(message: str, extra: dict | None = None) -> Iterator[None]:
    """Run a write, converting a lost uniqueness race into the standard 400 envelope.

    Every check-then-insert in the service layer -- "does this skill name / email /
    (mission, user) pair already exist?" followed by an INSERT -- is two statements with
    a gap. The pre-check and Django's `validate_constraints()` are both non-locking
    SELECTs, so a genuinely concurrent writer (a double-click, a client retry, two
    directors in the same settings screen) can slip between them and lose the race at
    the INSERT itself. `IntegrityError` is neither an `ApplicationError` nor a DRF
    exception, so `common.exception_handler` returns None for it and the caller gets an
    unenveloped HTML 500 instead of the same 400 the sequential path produces.

    The inner `atomic()` is a savepoint, not decoration: once Postgres raises, the
    transaction is aborted until something rolls back to a savepoint, so without one
    this would poison any enclosing `@transaction.atomic` and turn every subsequent
    statement -- including the next iteration of a loop -- into an `InTransaction` error
    too.

    Pass the message (and `extra`) the sequential path would have produced, so a client
    cannot tell the race apart from the ordinary duplicate.
    """
    try:
        with transaction.atomic():
            yield
    except IntegrityError:
        raise ApplicationError(message, extra=extra) from None
