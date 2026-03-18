"""Response handler that saves responses with template-driven output paths."""

import logging
import re
from pathlib import Path
from string import Template
from typing import Any, Self

from esi_link.handlers.errors import HandlerCreationError, HandlerValidationError
from esi_link.handlers.response.handler_abc import ResponseHandlerABC
from esi_link.handlers.response.helpers import check_required_keys
from esi_link.helpers.datetime_filename import file_safe_iso_datetime_string
from esi_link.helpers.save_text_file import save_text_file
from esi_link.models_and_protocols import (
    Response,
    ResponseHandlerConfig,
)

logger = logging.getLogger(__name__)


class TemplatedFilenameResponseHandler(ResponseHandlerABC):
    """Save response text to disk using a template-generated output path.

    The configured template is rendered using ``string.Template.safe_substitute``.
    Template values include:

    - Request metadata, e.g. ``request_id`` and ``operation_id``
    - Request parameters, prefixed with ``path_``, ``query_``, and ``runtime_query_``
    - Selected response metadata, e.g. ``status_code`` and ``received_at``
    - Optional user-provided values from config ``template_values``

    The rendered output path is normalized to filesystem-safe ASCII and constrained to
    a maximum filename length. Nested directories are supported but must resolve under
    ``output_dir``.
    """

    name = "esi-link:templated_filename"
    MAX_FILENAME_LENGTH = 180
    _SAFE_CHAR_RE = re.compile(r"[^A-Za-z0-9._-]+")

    def __init__(
        self,
        config: ResponseHandlerConfig,
        output_dir: Path,
        file_name_template: str,
        template_values: dict[str, str],
        overwrite: bool = False,
    ) -> None:
        """Initialize the templated response handler.

        Args:
            config: Handler config model for this instance.
            output_dir: Base output directory for rendered paths.
            file_name_template: Template string used for output path rendering.
            template_values: User-supplied key/value pairs available to the template.
            overwrite: Whether existing files may be overwritten.
        """
        self.config = config
        self.output_dir = output_dir
        self.file_name_template = file_name_template
        self.template_values = template_values
        self.overwrite = overwrite
        self.output_file: Path | None = None

    @staticmethod
    def _check_directory(output_dir: str) -> Path:
        """Validate and normalize the output directory path."""
        output_path = Path(output_dir).expanduser().resolve()
        if output_path.is_file():
            raise ValueError(
                f"output_dir '{output_dir}' resolves to a file, but must be a directory."
            )
        return output_path

    @classmethod
    def _stringify_template_values(
        cls,
        values: dict[str, Any],
    ) -> dict[str, str]:
        """Convert configured template values to strings for template substitution."""
        return {str(key): str(value) for key, value in values.items()}

    @classmethod
    def _sanitize_template_value(cls, value: str) -> str:
        """Sanitize a template substitution value without forcing non-empty output."""
        ascii_only = value.encode("ascii", "ignore").decode("ascii")
        cleaned = cls._SAFE_CHAR_RE.sub("_", ascii_only)
        cleaned = re.sub(r"_+", "_", cleaned)
        return cleaned.strip("._ ")

    @classmethod
    def _sanitize_template_mapping(cls, mapping: dict[str, str]) -> dict[str, str]:
        """Sanitize all template values before rendering.

        This prevents user-provided values from creating unexpected path segments.
        """
        return {
            key: cls._sanitize_template_value(value) for key, value in mapping.items()
        }

    @classmethod
    def _sanitize_component(cls, value: str) -> str:
        """Sanitize one path component to a conservative filesystem-safe ASCII set."""
        ascii_only = value.encode("ascii", "ignore").decode("ascii")
        cleaned = cls._SAFE_CHAR_RE.sub("_", ascii_only)
        cleaned = re.sub(r"_+", "_", cleaned)
        cleaned = cleaned.strip("._ ")
        return cleaned or "unnamed"

    @classmethod
    def _clip_filename(cls, filename: str, max_len: int) -> str:
        """Clip a filename while preserving extension when possible."""
        if len(filename) <= max_len:
            return filename

        stem, dot, suffix = filename.rpartition(".")
        if not dot:
            return filename[:max_len].rstrip("._ ") or "unnamed"

        suffix = cls._sanitize_component(suffix)
        allowed_stem_len = max_len - len(suffix) - 1
        if allowed_stem_len <= 0:
            return ("unnamed"[:max_len]).rstrip("._ ") or "unnamed"

        stem = cls._sanitize_component(stem)
        stem = stem[:allowed_stem_len].rstrip("._ ") or "unnamed"
        return f"{stem}.{suffix}"

    @staticmethod
    def _as_safe_iso(iso_value: str | None) -> str:
        """Convert an ISO string to a filename-safe variant."""
        if not iso_value:
            return "unknown"
        return file_safe_iso_datetime_string(iso_value)

    @classmethod
    def _build_template_context(cls, response: Response) -> dict[str, str]:
        """Build a flat context dictionary from request/response fields."""
        http_response = response.http_response
        runtime_info = response.runtime_info
        request = response.request

        context: dict[str, str] = {
            "request_id": str(request.request_id),
            "operation_id": request.operation_id,
            "auth_character_id": (
                str(request.auth_character_id)
                if request.auth_character_id is not None
                else "none"
            ),
            "path_url": runtime_info.path_url,
            "method": runtime_info.method,
            "is_paged": str(runtime_info.is_paged),
            "is_auth": str(runtime_info.is_auth),
            "status_code": (
                str(http_response.status_code) if http_response else "NO_RESPONSE"
            ),
            "received_at": (
                cls._as_safe_iso(http_response.received_at.format_iso())
                if http_response
                else "unknown"
            ),
            "etag": http_response.etag if http_response and http_response.etag else "",
            "cache_control": (
                http_response.cache_control
                if http_response and http_response.cache_control
                else ""
            ),
            "last_modified": (
                http_response.last_modified
                if http_response and http_response.last_modified
                else ""
            ),
            "expires": (
                cls._as_safe_iso(http_response.expires)
                if http_response and http_response.expires
                else ""
            ),
            "date": (
                cls._as_safe_iso(http_response.date)
                if http_response and http_response.date
                else ""
            ),
            "content_type": (
                (http_response.headers.get("Content-Type") if http_response else None)
                or (
                    http_response.headers.get("content-type") if http_response else None
                )
                or ""
            ),
            "cache_status": str(runtime_info.metrics.cache_response_status or ""),
            "cache_action": str(runtime_info.metrics.cache_action or ""),
            "task_duration": f"{runtime_info.metrics.task_duration:.6f}",
            "handlers_duration": f"{runtime_info.metrics.handlers_duration:.6f}",
            "paged_request_count": str(runtime_info.metrics.paged_request_count),
        }

        for key, value in request.path_parameters.items():
            context[f"path_{key}"] = str(value)
        for key, value in request.query_parameters.items():
            context[f"query_{key}"] = str(value)
        for key, value in runtime_info.additional_query_params.items():
            context[f"runtime_query_{key}"] = str(value)

        return context

    @classmethod
    def _sanitize_relative_path(
        cls,
        rendered_path: str,
        max_filename_length: int,
    ) -> Path:
        """Sanitize a rendered template path while preserving relative directory layout."""
        normalized = rendered_path.replace("\\", "/").strip()
        relative = Path(normalized)

        safe_parts: list[str] = []
        for part in relative.parts:
            if part in {"", "."}:
                continue
            if part == "..":
                raise ValueError("Template path cannot contain '..' segments.")
            safe_parts.append(cls._sanitize_component(part))

        if not safe_parts:
            safe_parts = ["response.json"]

        safe_parts[-1] = cls._clip_filename(safe_parts[-1], max_filename_length)
        return Path(*safe_parts)

    @classmethod
    def _resolve_output_file(
        cls,
        output_dir: Path,
        rendered_path: str,
        max_filename_length: int,
    ) -> Path:
        """Resolve the final output path and guarantee containment under output_dir."""
        relative_path = cls._sanitize_relative_path(
            rendered_path=rendered_path,
            max_filename_length=max_filename_length,
        )
        output_file = (output_dir / relative_path).resolve()
        if not output_file.is_relative_to(output_dir):
            raise ValueError("Rendered output path escapes output_dir.")
        return output_file

    @classmethod
    def _render_template_path(
        cls,
        file_name_template: str,
        template_context: dict[str, str],
        max_filename_length: int,
        output_dir: Path,
    ) -> Path:
        """Render template using safe_substitute and resolve to a safe output path."""
        rendered = Template(file_name_template).safe_substitute(template_context)
        return cls._resolve_output_file(
            output_dir=output_dir,
            rendered_path=rendered,
            max_filename_length=max_filename_length,
        )

    async def __call__(self, response: Response) -> Response:
        """Render the file path template and save the response text to disk."""
        template_context = self._build_template_context(response)
        template_context.update(self.template_values)
        template_context = self._sanitize_template_mapping(template_context)
        output_file = self._render_template_path(
            file_name_template=self.file_name_template,
            template_context=template_context,
            max_filename_length=self.MAX_FILENAME_LENGTH,
            output_dir=self.output_dir,
        )

        if response.http_response is not None:
            body_text = response.http_response.body_text
        else:
            body_text = response.model_dump_json(indent=2)

        file_path = save_text_file(
            text=body_text,
            output_path=output_file.parent,
            file_name=output_file.name,
            overwrite=self.overwrite,
        )
        self.output_file = file_path
        logger.info(
            "Response saved to %s with template '%s'",
            file_path,
            self.file_name_template,
        )
        return response

    @classmethod
    def from_config(cls, config: ResponseHandlerConfig) -> Self:
        """Create a templated filename handler from configuration."""
        try:
            output_dir = cls._check_directory(config.config["output_dir"])
            file_name_template = config.config["file_name_template"]
            raw_template_values = config.config.get("template_values", {})
            overwrite = config.config.get("overwrite", False)
            template_values = cls._stringify_template_values(raw_template_values)
        except KeyError as exc:
            raise HandlerCreationError(f"Missing required config key: {exc}") from exc
        except Exception as exc:
            raise HandlerCreationError(
                f"An error occurred while creating the handler: {exc}"
            ) from exc
        return cls(
            config=config,
            output_dir=output_dir,
            file_name_template=file_name_template,
            template_values=template_values,
            overwrite=overwrite,
        )

    @classmethod
    def validate_config(cls, config: ResponseHandlerConfig) -> None:
        """Validate the handler configuration schema and types."""
        expected_keys = {"output_dir", "file_name_template"}
        if "overwrite" in config.config:
            expected_keys.add("overwrite")
        if "template_values" in config.config:
            expected_keys.add("template_values")
        check_required_keys(config=config, required_keys=expected_keys)

        output_dir = config.config["output_dir"]
        file_name_template = config.config["file_name_template"]

        if not isinstance(output_dir, str):
            raise HandlerValidationError(
                "output_dir must be a string.",
                config=config.model_dump(),
            )
        if not isinstance(file_name_template, str):
            raise HandlerValidationError(
                "file_name_template must be a string.",
                config=config.model_dump(),
            )

        if "overwrite" in config.config and not isinstance(
            config.config["overwrite"], bool
        ):
            raise HandlerValidationError(
                "overwrite must be a boolean.",
                config=config.model_dump(),
            )

        if "template_values" in config.config:
            template_values = config.config["template_values"]
            if not isinstance(template_values, dict):
                raise HandlerValidationError(
                    "template_values must be a dictionary.",
                    config=config.model_dump(),
                )
            for key, value in template_values.items():
                if not isinstance(key, str):
                    raise HandlerValidationError(
                        "template_values keys must be strings.",
                        config=config.model_dump(),
                    )
                if not isinstance(value, str | int | float | bool):
                    raise HandlerValidationError(
                        "template_values values must be scalar types.",
                        config=config.model_dump(),
                    )
