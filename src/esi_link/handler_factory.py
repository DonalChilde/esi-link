"""Handler factory functions for creating ResponseHandlerConfig and ResponseGroupHandlerConfig instances."""

from pathlib import Path

from esi_link.models_and_protocols import (
    ResponseGroupHandlerConfig,
    ResponseHandlerConfig,
)


def save_group_stats(
    output_dir: Path,
    filename_template: str = "${iso_response_date}-${request_group_id}-GROUP-STATS.yaml",
    overwrite: bool = False,
) -> ResponseGroupHandlerConfig:
    """Example ResponseGroupHandlerConfig for the ResponseGroupSummaryToFileHandler.

    This config specifies the output directory, filename template, and whether to overwrite existing files.
    The filename_template can include tokens that will be filled in with values from the response group.
    For example, a template of "${iso_response_date}-${request_group_id}-GROUP-STATS.yaml"
    would create files like "2024-06-01T12_34_56-abc123-GROUP-STATS.yaml".
    """
    return ResponseGroupHandlerConfig(
        name="esi-link:response_group_summary_to_file_handler",
        config={
            "output_dir": str(output_dir),
            "filename_template": filename_template,
            "overwrite": overwrite,
        },
    )


def save_group_as_jsonl(
    output_dir: Path,
    filename_template: str = "${iso_response_date}-${request_group_id}-GROUP.jsonl",
    overwrite: bool = False,
) -> ResponseGroupHandlerConfig:
    """Example ResponseGroupHandlerConfig for the JsonlGroupSaver.

    This config specifies the output directory, filename template, and whether to overwrite existing files.
    The filename_template can include tokens that will be filled in with values from the response group.
    For example, a template of "${iso_response_date}-${request_group_id}-GROUP.jsonl"
    would create files like "2024-06-01T12_34_56-abc123-GROUP.jsonl".
    """
    return ResponseGroupHandlerConfig(
        name="esi-link:jsonl_group_saver",
        config={
            "output_dir": str(output_dir),
            "filename_template": filename_template,
            "overwrite": overwrite,
        },
    )


def only_on_error_file_response(
    output_dir: Path,
    filename_template: str = "${iso_response_date}-${operation_id}-${request_id}.json",
    overwrite: bool = False,
) -> ResponseHandlerConfig:
    """Example ResponseHandlerConfig for the OnlyOnErrorFileSaverResponseHandler.

    This config specifies the output directory, filename template, and whether to overwrite existing files.
    The filename_template can include tokens that will be filled in with values from the response.
    For example, a template of "${iso_response_date}-${operation_id}-${request_id}.json"
    would create files like "2024-06-01T12_34_56-GetStatus-1234_WITH_ERRORS.json".
    """
    return ResponseHandlerConfig(
        name="esi-link:error_only_file_saver",
        config={
            "output_dir": str(output_dir),
            "filename_template": filename_template,
            "overwrite": overwrite,
        },
    )


def debug_file_response(
    output_dir: Path, overwrite: bool = False
) -> ResponseHandlerConfig:
    """Example ResponseHandlerConfig for the DebugFileSaverResponseHandler.

    This config specifies the output directory and whether to overwrite existing files.
    The filename template is fixed to "${iso_response_date}-${operation_id}-${request_id}-DEBUG.json".
    The DebugFileSaverResponseHandler saves the full response as json, regardless of
    whether there are errors or not, to provide maximum information for debugging
    purposes. If there are errors, the filename stem will be suffixed with "_WITH_ERRORS".
    """
    return ResponseHandlerConfig(
        name="esi-link:debug_file_saver",
        config={
            "output_dir": str(output_dir),
            "filename_template": "${iso_response_date}-${operation_id}-${request_id}-DEBUG.json",
            "overwrite": overwrite,
        },
    )


def standard_file_response(
    output_dir: Path,
    filename_template: str = "${iso_response_date}-${operation_id}-${request_id}-STANDARD.json",
    overwrite: bool = False,
) -> ResponseHandlerConfig:
    """Example ResponseHandlerConfig for the StandardFileSaverResponseHandler.

    This config specifies the output directory, filename template, and whether to overwrite existing files.
    The filename_template can include tokens that will be filled in with values from the response.
    For example, a template of "${iso_response_date}-${operation_id}-${request_id}-STANDARD.json"
    would create files like "2024-06-01T12_34_56-GetStatus-1234-STANDARD.json".

    The StandardFileSaverResponseHandler saves the http response body text to a file at
    the output path generated from the template. If there are any errors in the response
    (network exceptions, http response is None, etc), then saves the entire response as
    json instead, to capture the error information. In this case, the file name will still
    be generated from the template, but will have the "_WITH_ERRORS" added to the file stem.
    """
    return ResponseHandlerConfig(
        name="esi-link:standard_file_saver",
        config={
            "output_dir": str(output_dir),
            "filename_template": filename_template,
            "overwrite": overwrite,
        },
    )


def detailed_file_response(
    output_dir: Path,
    filename_template: str = "${iso_response_date}-${operation_id}-${request_id}-DETAILED.json",
    overwrite: bool = False,
) -> ResponseHandlerConfig:
    """Example ResponseHandlerConfig for the DetailedFileSaverResponseHandler.

    This config specifies the output directory, filename template, and whether to overwrite existing files.
    The DetailedFileSaverResponseHandler saves detailed information about the response to a file at
    the output path generated from the template. The detailed information includes the
    fields from the request, the http response body text, and the download date.
    If there are any errors in the response (network exceptions, http response is None, etc),
    then saves the entire response as json instead, to capture the error information.
    In this case, the file name will still be generated from the template, but will have
    the suffix "_WITH_ERRORS" added to it, before the file extension.

    The filename_template can include tokens that will be filled in with values from the response.
    For example, a template of "${iso_response_date}-${operation_id}-${request_id}-DETAILED.json"
    would create files like "2024-06-01T12_34_56-GetStatus-1234-DETAILED.json".
    """
    return ResponseHandlerConfig(
        name="esi-link:detailed_file_saver",
        config={
            "output_dir": str(output_dir),
            "filename_template": filename_template,
            "overwrite": overwrite,
        },
    )
