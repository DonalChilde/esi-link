# """Indexed operation summaries are simplified representations of ESI operations."""

# from typing import TypedDict

# from esi_link.models_and_protocols import IndexedEsiSchema


# class IndexedOperationSummary(TypedDict):
#     """A summary of an indexed operation, containing only the most essential information."""

#     operation_id: str
#     method: str
#     description: str
#     tags: list[str]
#     auth_required: bool
#     is_paged: bool


# def collect_operation_summaries(
#     indexed_schema: IndexedEsiSchema,
# ) -> list[IndexedOperationSummary]:
#     """Collect summaries of all operations in the indexed ESI schema."""
#     operation_summaries: list[IndexedOperationSummary] = []
#     for operation_id, operation in indexed_schema.operations.items():
#         summary = IndexedOperationSummary(
#             operation_id=operation_id,
#             method=operation.method,
#             description=operation.description,
#             tags=operation.tags,
#             auth_required=operation.auth_required,
#             is_paged=operation.is_paged,
#         )
#         operation_summaries.append(summary)
#     return operation_summaries


# def summaries_by_tag(
#     operation_summaries: list[IndexedOperationSummary],
# ) -> dict[str, list[IndexedOperationSummary]]:
#     """Organize operation summaries by their tags."""
#     summaries_by_tag: dict[str, list[IndexedOperationSummary]] = {}
#     for summary in operation_summaries:
#         for tag in summary["tags"]:
#             if tag not in summaries_by_tag:
#                 summaries_by_tag[tag] = []
#             summaries_by_tag[tag].append(summary)
#     return summaries_by_tag
