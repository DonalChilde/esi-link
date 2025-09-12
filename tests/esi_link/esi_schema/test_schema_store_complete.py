"""Unit tests for SchemaStore and SchemaStoreData."""

# pyright: basic
import json
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from esi_link.esi_schema.schema_store import SchemaStore, SchemaStoreData


def test_schema_store_loads_from_schema_file(tmp_path: Path):
    """SchemaStore loads schema from file."""
    schema_path = tmp_path / "esi_schema.json"
    dummy_schema: dict[str, Any] = {"openapi": "3.0.0", "info": {"title": "Dummy"}}
    download_date = "Tue, 26 Aug 2025 00:00:00 GMT"
    schema_path.write_text(json.dumps(dummy_schema))
    store = SchemaStore.from_schema_file(
        schema_path=schema_path, download_date=download_date, store_path=None
    )
    assert store.esi_schema == dummy_schema
    assert store.download_date == "Tue, 26 Aug 2025 00:00:00 GMT"  # RFC 2822 format
    assert isinstance(store.schema_id, UUID)


def test_schema_store_loads_from_schema_file_and_save(tmp_path: Path):
    """SchemaStore loads schema from file."""
    schema_path = tmp_path / "esi_schema.json"
    store_path = tmp_path / "schema_store.json"
    dummy_schema: dict[str, Any] = {"openapi": "3.0.0", "info": {"title": "Dummy"}}
    download_date = "Tue, 26 Aug 2025 00:00:00 GMT"
    schema_path.write_text(json.dumps(dummy_schema))
    store = SchemaStore.from_schema_file(
        schema_path=schema_path, download_date=download_date, store_path=store_path
    )
    assert store.esi_schema == dummy_schema
    assert store.download_date == "Tue, 26 Aug 2025 00:00:00 GMT"  # RFC 2822 format
    assert isinstance(store.schema_id, UUID)
    assert store_path.is_file()
    loaded_data = json.loads(store_path.read_text())
    assert loaded_data["esi_schema"] == dummy_schema
    assert loaded_data["download_date"] == "Tue, 26 Aug 2025 00:00:00 GMT"


def test_schema_store_loads_from_obj(tmp_path: Path):
    """SchemaStore loads schema from a dictionary object."""
    dummy_schema: dict[str, Any] = {"openapi": "3.0.0", "info": {"title": "Dummy"}}
    download_date = "Tue, 26 Aug 2025 00:00:00 GMT"
    store = SchemaStore.from_obj(
        obj=dummy_schema, download_date=download_date, store_path=None
    )
    assert store.esi_schema == dummy_schema
    assert store.download_date == "Tue, 26 Aug 2025 00:00:00 GMT"  # RFC 2822 format
    assert isinstance(store.schema_id, UUID)


def test_schema_store_loads_from_obj_and_save(tmp_path: Path):
    """SchemaStore loads schema from a dictionary object and saves it."""
    dummy_schema: dict[str, Any] = {"openapi": "3.0.0", "info": {"title": "Dummy"}}
    download_date = "Tue, 26 Aug 2025 00:00:00 GMT"
    store_path = tmp_path / "schema_store.json"
    store = SchemaStore.from_obj(
        obj=dummy_schema, download_date=download_date, store_path=store_path
    )
    assert store.esi_schema == dummy_schema
    assert store.download_date == "Tue, 26 Aug 2025 00:00:00 GMT"  # RFC 2822 format
    assert isinstance(store.schema_id, UUID)
    assert (tmp_path / "schema_store.json").is_file()
    loaded_data = json.loads(store_path.read_text())
    assert loaded_data["esi_schema"] == dummy_schema
    assert loaded_data["download_date"] == "Tue, 26 Aug 2025 00:00:00 GMT"


def test_schema_store_download(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """SchemaStore downloads schema if file_path is None."""
    dummy_schema: dict[str, Any] = {"openapi": "3.0.1", "info": {"title": "Downloaded"}}

    def fake_download_text(url: str) -> str:
        return json.dumps(dummy_schema)

    monkeypatch.setattr(
        "esi_link.esi_schema.schema_store.download_text",
        fake_download_text,
    )

    class MockInstant:
        @staticmethod
        def now():
            class MockDateTime:
                def format_rfc2822(self):
                    return "Wed, 27 Aug 2025 00:00:00 GMT"

            return MockDateTime()

    monkeypatch.setattr(
        "esi_link.esi_schema.schema_store.Instant",
        MockInstant,
    )
    store = SchemaStore.from_download(store_path=None)
    assert store.esi_schema == dummy_schema
    assert store.download_date == "Wed, 27 Aug 2025 00:00:00 GMT"
    assert isinstance(store.schema_id, UUID)


def test_schema_store_update(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """SchemaStore.update downloads and saves new schema."""
    schema_path = tmp_path / "esi_schema.json"
    dummy_schema: dict[str, Any] = {"openapi": "3.0.0", "info": {"title": "Dummy"}}
    dummy_json = json.dumps(
        {
            "id_": str(UUID(int=1)),
            "download_date": "Thu, 28 Aug 2025 00:00:00 GMT",
            "esi_schema": dummy_schema,
        }
    )
    schema_path.write_text(dummy_json)

    def fake_download_text(url: str) -> str:
        return json.dumps({"openapi": "3.0.2", "info": {"title": "Updated"}})

    monkeypatch.setattr(
        "esi_link.esi_schema.schema_store.download_text",
        fake_download_text,
    )

    class MockInstant:
        @staticmethod
        def now():
            class MockDateTime:
                def format_rfc2822(self):
                    return "Fri, 29 Aug 2025 00:00:00 GMT"

            return MockDateTime()

    monkeypatch.setattr(
        "esi_link.esi_schema.schema_store.Instant",
        MockInstant,
    )
    store = SchemaStore(schema_path)
    store.update()
    assert store.esi_schema["openapi"] == "3.0.2"
    assert store.download_date == "Fri, 29 Aug 2025 00:00:00 GMT"
    saved = json.loads(schema_path.read_text())
    assert saved["esi_schema"]["openapi"] == "3.0.2"
    assert saved["download_date"] == "Fri, 29 Aug 2025 00:00:00 GMT"


def test_save_store_data_writes_file(tmp_path: Path):
    """_save_store_data writes schema data to file correctly."""
    store_path = tmp_path / "esi_schema.json"
    download_date = "Sat, 30 Aug 2025 00:00:00 GMT"
    dummy_schema: dict[str, Any] = {"openapi": "3.0.0", "info": {"title": "Dummy"}}
    store = SchemaStore.from_obj(
        obj=dummy_schema,
        store_path=store_path,
        download_date=download_date,
    )

    store._save_store_data()
    saved = json.loads(store_path.read_text())
    assert isinstance(UUID(saved["id_"]), UUID)
    assert saved["download_date"] == "Sat, 30 Aug 2025 00:00:00 GMT"
    assert saved["esi_schema"] == dummy_schema


def test_save_store_data_raises_if_store_data_none(tmp_path: Path):
    """_save_store_data raises ValueError if _store_data is None."""
    store_path = tmp_path / "esi_schema.json"
    download_date = "Sat, 30 Aug 2025 00:00:00 GMT"
    dummy_schema: dict[str, Any] = {"openapi": "3.0.0", "info": {"title": "Dummy"}}
    store = SchemaStore.from_obj(
        obj=dummy_schema,
        store_path=store_path,
        download_date=download_date,
    )
    store._store_data = None
    with pytest.raises(ValueError, match="ESI schema is not loaded. Nothing to save."):
        store._save_store_data()


# TODO this function needs to be monkeypatched to keep it from actually downloading the schema
# def test_save_store_data_raises_if_file_path_none():
#     """_save_store_data raises ValueError if file_path is None."""
#     store = SchemaStore.from_download(store_path=None)
#     dummy_schema: dict[str, Any] = {"openapi": "3.0.0", "info": {"title": "Dummy"}}
#     store._store_data = SchemaStoreData(
#         id_=UUID(int=3),
#         download_date="Sun, 31 Aug 2025 00:00:00 GMT",
#         esi_schema=dummy_schema,
#     )
#     with pytest.raises(ValueError, match="SchemaStore file_path is not set."):
#         store._save_store_data()


def test_save_store_data_respects_indent(tmp_path: Path):
    """_save_store_data respects indent_on_save argument."""
    store_path = tmp_path / "esi_schema.json"
    download_date = "Sat, 30 Aug 2025 00:00:00 GMT"
    dummy_schema: dict[str, Any] = {"openapi": "3.0.0", "info": {"title": "Dummy"}}
    store = SchemaStore.from_obj(
        obj=dummy_schema,
        store_path=store_path,
        download_date=download_date,
        indent_on_save=2,
    )
    text = store_path.read_text()
    assert "\n  " in text
    loaded = json.loads(text)
    assert loaded["esi_schema"]["openapi"] == "3.0.0"


def test_load_store_data_raises_if_file_missing(tmp_path: Path):
    """_load_store_data raises ValueError if file is missing."""
    store_path = tmp_path / "esi_schema.json"
    download_date = "Sat, 30 Aug 2025 00:00:00 GMT"
    dummy_schema: dict[str, Any] = {"openapi": "3.0.0", "info": {"title": "Dummy"}}
    store = SchemaStore.from_obj(
        obj=dummy_schema,
        store_path=store_path,
        download_date=download_date,
        indent_on_save=2,
    )
    # Remove file if it exists
    if store_path.exists():
        store_path.unlink()
    with pytest.raises(ValueError, match="SchemaStore file not found"):
        store._load_store_data()


def test_load_store_data_raises_if_invalid_schema(tmp_path: Path):
    """_load_store_data raises ValueError if schema is invalid."""
    store_path = tmp_path / "esi_schema.json"
    store_path.write_text(
        json.dumps(
            {
                "id_": str(UUID(int=5)),
                "download_date": "Mon, 02 Sep 2025 00:00:00 GMT",
                "schema_": {},
            }
        )
    )

    with pytest.raises(ValueError):
        store = SchemaStore(store_path)


def test_download_schema_raises_if_invalid(monkeypatch: pytest.MonkeyPatch):
    """_download_schema raises ValueError if schema is missing 'openapi'."""

    def fake_download_text(url: str) -> str:
        return json.dumps({"info": {"title": "No OpenAPI"}})

    monkeypatch.setattr(
        "esi_link.esi_schema.schema_store.download_text",
        fake_download_text,
    )

    with pytest.raises(ValueError):
        store = SchemaStore.from_download(store_path=None)
