from pathlib import Path

from pydantic import BaseModel, Field


class Example(BaseModel):
    file_path: Path


def test_pydantic_coercion():
    example = Example(file_path="foo/test.txt")
    assert isinstance(example.file_path, Path)
