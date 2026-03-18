"""This module provides helper functions for serializing and deserializing Pydantic models to and from YAML files."""

from pathlib import Path

from pydantic import BaseModel
from yaml import safe_dump, safe_load


def serialize_as_yaml(
    obj: BaseModel,
    output_dir: Path,
    filename: str,
    *,
    overwrite: bool = False,
    indent: int | None = None,
) -> Path:
    """Serialize a Pydantic model to YAML and save it to a file.

    Args:
        obj: The Pydantic model to serialize.
        output_dir: The directory where the YAML file will be saved.
        filename: The name of the YAML file.
        overwrite: Whether to overwrite the file if it already exists.
        indent: The number of spaces to use for indentation in the YAML file. If None,
            pyyaml's default indentation will be used.

    Returns:
        The path to the saved YAML file.
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
        safe_dump(obj.model_dump(mode="json"), f, indent=indent)
    return output_path


def load_from_yaml(file_path: Path, model_cls: type[BaseModel]) -> BaseModel:
    """Load a Pydantic model from a YAML file.

    Args:
        file_path: The path to the YAML file.
        model_cls: The Pydantic model class to load.

    Returns:
        An instance of the Pydantic model.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"{file_path} does not exist.")
    if file_path.is_dir():
        raise IsADirectoryError(f"{file_path} is a directory, expected a file path.")
    with open(file_path) as f:
        return model_cls.model_validate(safe_load(f))
