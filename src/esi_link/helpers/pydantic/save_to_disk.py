"""Helper classes for models that can be saved to disk as JSON."""

import logging
from pathlib import Path
from typing import Self

from pydantic import BaseModel, RootModel

logger = logging.getLogger(__name__)


class RootModelToDisk(RootModel):  # pyright: ignore[reportMissingTypeArgument]
    """Base class for RootModels that can be saved to disk as JSON."""

    def save_to_disk(self, file_path: Path, overwrite: bool = False) -> None:
        """Save the model to disk as JSON."""
        if file_path.is_dir():
            logger.error(
                f"{file_path} is a directory, Unable to save file for Model {self.__class__.__name__}."
            )
            raise IsADirectoryError(
                f"{file_path} is a directory, Unable to save file for Model {self.__class__.__name__}."
            )
        if file_path.exists() and not overwrite:
            logger.error(
                f"{file_path} already exists and overwrite is False. Unable to save file for Model {self.__class__.__name__}."
            )
            raise FileExistsError(
                f"{file_path} already exists and overwrite is False. Unable to save file for Model {self.__class__.__name__}."
            )
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.model_dump_json(indent=2))
        except Exception as e:
            logger.exception(
                f"Error saving file {file_path} for Model {self.__class__.__name__}: {e}"
            )
            raise e

    @classmethod
    def load_from_disk(cls, file_path: Path) -> Self:
        """Load the model from disk as JSON."""
        if file_path.is_dir():
            logger.error(
                f"{file_path} is a directory, Unable to load file for Model {cls.__name__}."
            )
            raise IsADirectoryError(
                f"{file_path} is a directory, Unable to load file for Model {cls.__name__}."
            )
        if not file_path.exists():
            logger.error(
                f"{file_path} does not exist. Unable to load file for Model {cls.__name__}."
            )
            raise FileNotFoundError(
                f"{file_path} does not exist. Unable to load file for Model {cls.__name__}."
            )
        try:
            with open(file_path, encoding="utf-8") as f:
                return cls.model_validate_json(f.read())
        except Exception as e:
            logger.exception(
                f"Error loading file {file_path} to Model {cls.__name__}: {e}"
            )
            raise e


class BaseModelToDisk(BaseModel):
    """Base class for BaseModels that can be saved to disk as JSON."""

    def save_to_disk(self, file_path: Path, overwrite: bool = False) -> None:
        """Save the model to disk as JSON."""
        if file_path.is_dir():
            logger.error(
                f"{file_path} is a directory, Unable to save file for Model {self.__class__.__name__}."
            )
            raise IsADirectoryError(
                f"{file_path} is a directory, Unable to save file for Model {self.__class__.__name__}."
            )
        if file_path.exists() and not overwrite:
            logger.error(
                f"{file_path} already exists and overwrite is False. Unable to save file for Model {self.__class__.__name__}."
            )
            raise FileExistsError(
                f"{file_path} already exists and overwrite is False. Unable to save file for Model {self.__class__.__name__}."
            )
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.model_dump_json(indent=2))
        except Exception as e:
            logger.exception(
                f"Error saving file {file_path} for Model {self.__class__.__name__}: {e}"
            )
            raise e

    @classmethod
    def load_from_disk(cls, file_path: Path) -> Self:
        """Load the model from disk as JSON."""
        if file_path.is_dir():
            logger.error(
                f"{file_path} is a directory, Unable to load file for Model {cls.__name__}."
            )
            raise IsADirectoryError(
                f"{file_path} is a directory, Unable to load file for Model {cls.__name__}."
            )
        if not file_path.exists():
            logger.error(
                f"{file_path} does not exist. Unable to load file for Model {cls.__name__}."
            )
            raise FileNotFoundError(
                f"{file_path} does not exist. Unable to load file for Model {cls.__name__}."
            )
        try:
            with open(file_path, encoding="utf-8") as f:
                return cls.model_validate_json(f.read())
        except Exception as e:
            logger.exception(
                f"Error loading file {file_path} to Model {cls.__name__}: {e}"
            )
            raise e
