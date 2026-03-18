"""This module provides helper functions for serializing and deserializing Pydantic models to and from JSON files."""

from pathlib import Path

from pydantic import BaseModel


def serialize_as_json(
    obj: BaseModel,
    output_dir: Path,
    filename: str,
    *,
    overwrite: bool = False,
    indent: int = 2,
) -> Path:
    """Serialize a Pydantic model to JSON and save it to a file.

    Args:
        obj: The Pydantic model to serialize.
        output_dir: The directory where the JSON file will be saved.
        filename: The name of the JSON file.
        overwrite: Whether to overwrite the file if it already exists.
        indent: The number of spaces to use for indentation in the JSON file.

    Returns:
        The path to the saved JSON file.
    """
    if output_dir.exists() and not output_dir.is_dir():
        raise NotADirectoryError(f"{output_dir} exists and is not a directory.")
    output_path = output_dir / filename
    if output_path.is_dir():
        raise IsADirectoryError(f"{output_path} is a directory, expected a file path.")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"{output_path} already exists and overwrite is False.")
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(obj.model_dump_json(indent=indent))
    return output_path


def load_from_json[BASE_MODELS: BaseModel](
    file_path: Path, model_cls: type[BASE_MODELS]
) -> BASE_MODELS:
    """Load a Pydantic model from a JSON file.

    Args:
        file_path: The path to the JSON file.
        model_cls: The Pydantic model class to load.

    Returns:
        An instance of the Pydantic model.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"{file_path} does not exist.")
    if file_path.is_dir():
        raise IsADirectoryError(f"{file_path} is a directory, expected a file path.")
    with open(file_path) as f:
        return model_cls.model_validate_json(f.read())
