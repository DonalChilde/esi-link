from esi_link.v2.models import (
    IndexedEsiSchema,
    IndexedSchemaStore,
    SchemaManagerProtocol,
)
from esi_link.v2.settings import EsiLinkSettings, get_settings


class SchemaManager(SchemaManagerProtocol):
    def __init__(self, settings: EsiLinkSettings | None = None):
        self._settings = settings or get_settings()
        self._schema_store: IndexedSchemaStore | None = None
