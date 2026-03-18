from esi_link.handlers.errors import HandlerValidationError
from esi_link.models_and_protocols import ResponseHandlerConfig


def check_available_keys(
    config: ResponseHandlerConfig, required_keys: set[str]
) -> None:
    """Check the ResponseHandlerConfig for the required keys and their types."""
    keys = set(config.config.keys())
    missing_keys = required_keys - keys
    if missing_keys:
        raise HandlerValidationError(
            f"Missing required config keys: {missing_keys}", config=config.model_dump()
        )
    extra_keys = keys - required_keys
    if extra_keys:
        raise HandlerValidationError(
            f"Extra config keys not used by handler: {extra_keys}",
            config=config.model_dump(),
        )
