from whenever import Instant


# FIXME keep this until testing shows it is not needed with pydantic.
def get_current_instant() -> Instant:
    """Factory function to get current instant for default values.

    This function is used as a default_factory to avoid Pydantic issue with using a
    non-callable default for a non-serializable type.

    Returns:
        Current instant in time.
    """
    return Instant.now()
