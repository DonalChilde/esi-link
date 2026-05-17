"""Functions for validating requests and request groups."""

from copy import deepcopy
from dataclasses import replace
from string import Template

from esi_link.simplified_models import (
    EsiSchema,
    FailedRequestGroupValidation,
    FailedRequestValidation,
    Request,
    RequestGroup,
    ValidatedRequest,
    ValidatedRequestGroup,
)
from esi_link.simplified_protocols import SchemaManagerProtocol


def validate_request(
    request: Request,
    schema_manager: SchemaManagerProtocol,
    authorized_characters: set[int],
) -> ValidatedRequest | FailedRequestValidation:
    """Validates an individual request. If the request is valid, returns a ValidatedRequest. If the request is invalid, returns a FailedRequestValidation with the appropriate error messages."""
    in_process: ValidatedRequest | FailedRequestValidation = ValidatedRequest(
        created_on=request.created_on,
        request_id=request.request_id,
        actions_after_response=request.actions_after_response,  # TODO move to validation step after we have the schema, so we can validate that the actions are valid for the requested operation_id
    )
    in_process = _validate_request_schema(
        request, in_process, schema_manager=schema_manager
    )
    if isinstance(in_process, FailedRequestValidation):
        # If the schema validation failed, we don't need to do any further validation,
        # because the request is already invalid. We can just return the
        # FailedRequestValidation with the schema validation error.
        return in_process
    # Get the schema for use in the rest of the validation steps.
    assert in_process.compatibility_date is not None, (
        "compatibility_date should have been set in the schema validation step"
    )
    # Since the schema validation step passed, we know that the requested schema is
    # available in the schema manager, so this should not raise a SchemaNotFoundError.
    # If it does, it's an unexpected error and we can just let it propagate.
    schema = schema_manager.get_schema(
        compatibility_date=in_process.compatibility_date,
        at_or_after=in_process.at_or_after,
    ).esi_schema
    in_process = _validate_operation_id(request, in_process, schema=schema)
    if isinstance(in_process, FailedRequestValidation):
        # If the operation_id validation failed, we don't need to do any further validation, because the request is already invalid. We can just return the FailedRequestValidation with the operation_id validation error.
        return in_process
    in_process = _validate_path_parameters(request, in_process, schema=schema)
    in_process = _validate_query_parameters(request, in_process, schema=schema)
    in_process = _validate_body_parameters(request, in_process, schema=schema)
    in_process = _validate_authentication(
        request, in_process, schema=schema, authorized_characters=authorized_characters
    )
    in_process = _validate_language(request, in_process, schema=schema)
    # in_process = _validate_request_directory_template(request, in_process)
    # in_process = _validate_request_filename_template(request, in_process)
    in_process = _set_method(request, in_process, schema=schema)
    in_process = _set_url_template(request, in_process, schema=schema)
    in_process = _set_is_paged(request, in_process, schema=schema)
    in_process = _set_is_paged(request, in_process, schema=schema)
    in_process = _set_is_cached(request, in_process, schema=schema)
    in_process = _set_is_authentication_required(request, in_process, schema=schema)
    return in_process


def validate_request_group(
    request_group: RequestGroup,
    schema_manager: SchemaManagerProtocol,
    *,
    authorized_characters: set[int],
) -> ValidatedRequestGroup | FailedRequestGroupValidation:
    """Validates a request group and all of its individual requests. If the request group is valid, returns a ValidatedRequestGroup. If the request group is invalid, returns a FailedRequestGroupValidation with the appropriate error messages."""
    in_process: ValidatedRequestGroup | FailedRequestGroupValidation = (
        ValidatedRequestGroup(
            created_on=request_group.created_on,
            group_id=request_group.group_id,
            description=request_group.description,
            actions_after_response=request_group.actions_after_response,  # TODO move to validation step after we have the schema, so we can validate that the actions are valid for the requested operation_ids of the individual requests in the group
        )
    )
    # in_process = _validate_group_directory_template(request_group, in_process)
    # in_process = _validate_group_filename_template(request_group, in_process)
    if isinstance(in_process, FailedRequestGroupValidation):
        # If the group-level validation failed, we don't need to validate the individual requests, because the group is already invalid. We can just return the FailedRequestGroupValidation with the group-level errors.
        return in_process
    for request_id, request in request_group.requests.items():
        validated_request_or_failure = validate_request(
            request=request,
            schema_manager=schema_manager,
            authorized_characters=authorized_characters,
        )
        if isinstance(validated_request_or_failure, ValidatedRequest):
            in_process.requests[request_id] = validated_request_or_failure

        if isinstance(validated_request_or_failure, FailedRequestValidation):
            in_process.failed_request_validations[request_id] = (
                validated_request_or_failure
            )

    return in_process


# def _validate_group_directory_template(
#     request_group: RequestGroup,
#     inprocess_request_group: ValidatedRequestGroup | FailedRequestGroupValidation,
# ) -> ValidatedRequestGroup | FailedRequestGroupValidation:
#     """Validates the save_directory_template field of the request group, if applicable. If the template is invalid, returns a FailedRequestGroupValidation with the appropriate error message. If the template is valid, returns the inprocess_request_group unchanged."""
#     if request_group.save_directory_template is not None:
#         fail_msgs: list[str] = []
#         # Validate that the template is a valid directory path template.
#         # Because some of the variables that can be used in the template are not known
#         # until execution time, we can't fully validate the template at this point. However,
#         # we can validate that the template is a valid string template and that it only
#         # uses the allowed variables.

#         # TODO define this in a central place, probably the module that actually renders the template, and import it here.
#         available_variables = {"group_id", "created_on"}
#         template = Template(request_group.save_directory_template)
#         identifiers = template.get_identifiers()
#         fail_msgs: list[str] = []
#         for identifier in identifiers:
#             if identifier not in available_variables:
#                 fail_msgs.append(
#                     f"Invalid save_directory_template: invalid variable {identifier}"
#                 )
#         if fail_msgs:
#             if isinstance(inprocess_request_group, FailedRequestGroupValidation):
#                 fail_msgs = list(inprocess_request_group.errors) + fail_msgs
#             return FailedRequestGroupValidation(
#                 request_group=request_group,
#                 errors=tuple(fail_msgs),
#             )
#     # Update validated fields.
#     if isinstance(inprocess_request_group, ValidatedRequestGroup):
#         inprocess_request_group = deepcopy(inprocess_request_group)
#         inprocess_request_group = replace(
#             inprocess_request_group,
#             save_directory_template=request_group.save_directory_template,
#         )
#     return inprocess_request_group


# def _validate_group_filename_template(
#     request_group: RequestGroup,
#     inprocess_request_group: ValidatedRequestGroup | FailedRequestGroupValidation,
# ) -> ValidatedRequestGroup | FailedRequestGroupValidation:
#     """Validates the save_filename_template field of the request group, if applicable. If the template is invalid, returns a FailedRequestGroupValidation with the appropriate error message. If the template is valid, returns the inprocess_request_group unchanged."""
#     if request_group.save_filename_template is not None:
#         fail_msgs: list[str] = []
#         # Validate that the template is a valid filename template.
#         # Because some of the variables that can be used in the template are not known
#         # until execution time, we can't fully validate the template at this point. However,
#         # we can validate that the template is a valid string template and that it only
#         # uses the allowed variables.

#         # TODO define this in a central place, probably the module that actually renders the template, and import it here.
#         available_variables = {"group_id", "created_on"}
#         template = Template(request_group.save_filename_template)
#         identifiers = template.get_identifiers()
#         fail_msgs: list[str] = []
#         for identifier in identifiers:
#             if identifier not in available_variables:
#                 fail_msgs.append(
#                     f"Invalid save_filename_template: invalid variable {identifier}"
#                 )
#         if fail_msgs:
#             if isinstance(inprocess_request_group, FailedRequestGroupValidation):
#                 fail_msgs = list(inprocess_request_group.errors) + fail_msgs
#             return FailedRequestGroupValidation(
#                 request_group=request_group,
#                 errors=tuple(fail_msgs),
#             )
#     # Update validated fields.
#     if isinstance(inprocess_request_group, ValidatedRequestGroup):
#         inprocess_request_group = deepcopy(inprocess_request_group)
#         inprocess_request_group = replace(
#             inprocess_request_group,
#             save_filename_template=request_group.save_filename_template,
#         )
#     return inprocess_request_group


# def _validate_request_directory_template(
#     request: Request,
#     inprocess_request: ValidatedRequest | FailedRequestValidation,
# ) -> ValidatedRequest | FailedRequestValidation:
#     """Validates the save_directory_template field of the request, if applicable. If the template is invalid, returns a FailedRequestValidation with the appropriate error message. If the template is valid, returns the inprocess_request unchanged."""
#     if request.save_directory_template is not None:
#         fail_msgs: list[str] = []
#         # Validate that the template is a valid directory path template.
#         # Because some of the variables that can be used in the template are not known
#         # until execution time, we can't fully validate the template at this point. However,
#         # we can validate that the template is a valid string template and that it only
#         # uses the allowed variables.

#         # TODO define this in a central place, probably the module that actually renders the template, and import it here.
#         available_variables = {"request_id", "created_on"}
#         template = Template(request.save_directory_template)
#         identifiers = template.get_identifiers()
#         fail_msgs: list[str] = []
#         for identifier in identifiers:
#             if identifier not in available_variables:
#                 fail_msgs.append(
#                     f"Invalid save_directory_template: invalid variable {identifier}"
#                 )
#         if fail_msgs:
#             if isinstance(inprocess_request, FailedRequestValidation):
#                 fail_msgs = list(inprocess_request.errors) + fail_msgs
#             return FailedRequestValidation(
#                 request=request,
#                 errors=tuple(fail_msgs),
#             )
#     # Update validated fields.
#     if isinstance(inprocess_request, ValidatedRequest):
#         inprocess_request = deepcopy(inprocess_request)
#         inprocess_request = replace(
#             inprocess_request,
#             save_directory_template=request.save_directory_template,
#         )
#     return inprocess_request


# def _validate_request_filename_template(
#     request: Request,
#     inprocess_request: ValidatedRequest | FailedRequestValidation,
# ) -> ValidatedRequest | FailedRequestValidation:
#     """Validates the save_filename_template field of the request, if applicable. If the template is invalid, returns a FailedRequestValidation with the appropriate error message. If the template is valid, returns the inprocess_request unchanged."""
#     if request.save_filename_template is not None:
#         fail_msgs: list[str] = []
#         # Validate that the template is a valid filename template.
#         # Because some of the variables that can be used in the template are not known
#         # until execution time, we can't fully validate the template at this point. However,
#         # we can validate that the template is a valid string template and that it only
#         # uses the allowed variables.

#         # TODO define this in a central place, probably the module that actually renders the template, and import it here.
#         available_variables = {"request_id", "created_on"}
#         template = Template(request.save_filename_template)
#         identifiers = template.get_identifiers()
#         fail_msgs: list[str] = []
#         for identifier in identifiers:
#             if identifier not in available_variables:
#                 fail_msgs.append(
#                     f"Invalid save_filename_template: invalid variable {identifier}"
#                 )
#         if fail_msgs:
#             if isinstance(inprocess_request, FailedRequestValidation):
#                 fail_msgs = list(inprocess_request.errors) + fail_msgs
#             return FailedRequestValidation(
#                 request=request,
#                 errors=tuple(fail_msgs),
#             )
#     # Update validated fields.
#     if isinstance(inprocess_request, ValidatedRequest):
#         inprocess_request = deepcopy(inprocess_request)
#         inprocess_request = replace(
#             inprocess_request,
#             save_filename_template=request.save_filename_template,
#         )
#     return inprocess_request


def _validate_request_schema(
    request: Request,
    inprocess_request: ValidatedRequest | FailedRequestValidation,
    *,
    schema_manager: SchemaManagerProtocol,
) -> ValidatedRequest | FailedRequestValidation:
    """Validates that the requested schema is available in the schema manager.

    Because so many of the details of the request validation logic depend on the schema,
    we need to validate that the requested schema is available before we can do any further
    validation. If the requested schema is not available, returns a FailedRequestValidation
    with the appropriate error message.
    """
    available_schemas = schema_manager.available_schemas()
    if request.compatibility_date is None and request.at_or_after is None:
        # If no compatibility date or timestamp is provided, we can assume the latest
        # schema will be used, so we can just check that a schema is available.
        if not available_schemas:
            fail_msg = "No schemas are available in the schema manager."
            if isinstance(inprocess_request, FailedRequestValidation):
                fail_msgs = list(inprocess_request.errors) + [fail_msg]
            else:
                fail_msgs = [fail_msg]
            return FailedRequestValidation(
                request=request,
                errors=tuple(fail_msgs),
            )
        return inprocess_request

    if request.compatibility_date is not None:
        # If a compatibility date is provided, we need to check that there is a schema
        # with that compatibility date, and if a timestamp is also provided, that there
        # is a schema with that compatibility date and a timestamp at or after the provided timestamp.
        filtered_schemas = [
            schema_info
            for schema_info in available_schemas
            if schema_info.compatibility_date == request.compatibility_date
        ]
        if not filtered_schemas:
            fail_msg = f"Requested schema with compatibility date {request.compatibility_date} is not available."
            if isinstance(inprocess_request, FailedRequestValidation):
                fail_msgs = list(inprocess_request.errors) + [fail_msg]
            else:
                fail_msgs = [fail_msg]
            return FailedRequestValidation(
                request=request,
                errors=tuple(fail_msgs),
            )
        if request.at_or_after is not None:
            filtered_schemas = [
                schema_info
                for schema_info in filtered_schemas
                if schema_info.timestamp >= request.at_or_after
            ]
            if not filtered_schemas:
                fail_msg = f"Requested schema with compatibility date {request.compatibility_date} and timestamp after {request.at_or_after} is not available."
                if isinstance(inprocess_request, FailedRequestValidation):
                    fail_msgs = list(inprocess_request.errors) + [fail_msg]
                else:
                    fail_msgs = [fail_msg]
                return FailedRequestValidation(
                    request=request,
                    errors=tuple(fail_msgs),
                )
    if request.compatibility_date is None and request.at_or_after is not None:
        # invalid combination of parameters - after is provided without a compatibility date, so we don't know which schema to check for the timestamp against. We can fail this validation because it's an invalid request.
        fail_msg = f"Invalid request: 'after' parameter provided without a compatibility date, so we don't know which schema to check for the timestamp against."
        if isinstance(inprocess_request, FailedRequestValidation):
            fail_msgs = list(inprocess_request.errors) + [fail_msg]
        else:
            fail_msgs = [fail_msg]
        return FailedRequestValidation(
            request=request,
            errors=tuple(fail_msgs),
        )
    # Update validated fields.
    if isinstance(inprocess_request, ValidatedRequest):
        inprocess_request = deepcopy(inprocess_request)
        inprocess_request = replace(
            inprocess_request,
            compatibility_date=request.compatibility_date,
            after=request.at_or_after,
        )
    return inprocess_request


def _validate_operation_id(
    request: Request,
    inprocess_request: ValidatedRequest | FailedRequestValidation,
    *,
    schema: EsiSchema,
) -> ValidatedRequest | FailedRequestValidation:
    """Validates that the operation_id field of the request corresponds to a valid operation in the ESI OpenAPI schema. If the operation_id is invalid, returns a FailedRequestValidation with the appropriate error message. If the operation_id is valid, returns the inprocess_request unchanged."""
    available_operations = schema.operation_ids
    if request.operation_id not in available_operations:
        fail_msg = f"Requested operation_id {request.operation_id} is not available in the schema."
        if isinstance(inprocess_request, FailedRequestValidation):
            fail_msgs = list(inprocess_request.errors) + [fail_msg]
        else:
            fail_msgs = [fail_msg]
        return FailedRequestValidation(
            request=request,
            errors=tuple(fail_msgs),
        )
    # Update validated fields.
    if isinstance(inprocess_request, ValidatedRequest):
        inprocess_request = deepcopy(inprocess_request)
        inprocess_request = replace(
            inprocess_request,
            operation_id=request.operation_id,
        )
    return inprocess_request


def _validate_path_parameters(
    request: Request,
    inprocess_request: ValidatedRequest | FailedRequestValidation,
    *,
    schema: EsiSchema,
) -> ValidatedRequest | FailedRequestValidation:
    """Validates that the path parameters provided in the request are valid for the requested operation_id according to the ESI OpenAPI schema. If any path parameters are invalid, returns a FailedRequestValidation with the appropriate error messages. If all path parameters are valid, returns the inprocess_request unchanged."""
    operation = schema.get_operation_by_id(request.operation_id)
    assert operation is not None, (
        "operation should have been found in the operation_id validation step"
    )
    expected_path_parameters = {
        param["name"]: param for param in operation.path_parameters
    }
    given_path_parameters = deepcopy(request.path_parameters)
    # All path parameters defined in the schema must be present in the request, and must be of the correct type.
    fail_msgs: list[str] = []
    for param_name, param_schema in expected_path_parameters.items():
        if param_name not in given_path_parameters:
            fail_msgs.append(f"Missing required path parameter: {param_name}")
        else:
            if param_schema["type"] == "integer":
                if not isinstance(given_path_parameters[param_name], int):
                    fail_msgs.append(
                        f"Invalid type for path parameter {param_name}: expected integer, got {type(given_path_parameters[param_name]).__name__}"
                    )
            elif param_schema["type"] == "string":
                if not isinstance(given_path_parameters[param_name], str):
                    fail_msgs.append(
                        f"Invalid type for path parameter {param_name}: expected string, got {type(given_path_parameters[param_name]).__name__}"
                    )
            pass
    # If there are any validation errors, return a FailedRequestValidation with the error messages.
    if fail_msgs:
        if isinstance(inprocess_request, FailedRequestValidation):
            fail_msgs = list(inprocess_request.errors) + fail_msgs
        return FailedRequestValidation(
            request=request,
            errors=tuple(fail_msgs),
        )
    # Update validated fields.
    if isinstance(inprocess_request, ValidatedRequest):
        inprocess_request = deepcopy(inprocess_request)
        inprocess_request = replace(
            inprocess_request,
            path_parameters=given_path_parameters,
        )
    return inprocess_request


def _validate_query_parameters(
    request: Request,
    inprocess_request: ValidatedRequest | FailedRequestValidation,
    *,
    schema: EsiSchema,
) -> ValidatedRequest | FailedRequestValidation:
    """Validates that the query parameters provided in the request are valid for the requested operation_id according to the ESI OpenAPI schema. If any query parameters are invalid, returns a FailedRequestValidation with the appropriate error messages. If all query parameters are valid, returns the inprocess_request unchanged."""
    operation = schema.get_operation_by_id(request.operation_id)
    assert operation is not None, (
        "operation should have been found in the operation_id validation step"
    )
    expected_query_parameters = {
        param["name"]: param for param in operation.query_parameters
    }
    given_query_parameters = deepcopy(request.query_parameters)
    # No extra query parameters that are not defined in the schema can be present in the request.
    # All query parameters defined in the schema that are required must be present in the request.
    # and all query parameters defined in the schema that are present in the request must be of the correct type.
    fail_msgs: list[str] = []
    for param_name, param_value in given_query_parameters.items():
        if param_name not in expected_query_parameters:
            fail_msgs.append(f"Unexpected query parameter: {param_name}")
        else:
            param_schema = expected_query_parameters[param_name]
            if param_schema["type"] == "integer":
                if not isinstance(param_value, int):
                    fail_msgs.append(
                        f"Invalid type for query parameter {param_name}: expected integer, got {type(param_value).__name__}"
                    )
            elif param_schema["type"] == "string":
                if not isinstance(param_value, str):
                    fail_msgs.append(
                        f"Invalid type for query parameter {param_name}: expected string, got {type(param_value).__name__}"
                    )
    for param_name, param_schema in expected_query_parameters.items():
        if (
            param_schema.get("required", False)
            and param_name not in given_query_parameters
        ):
            fail_msgs.append(f"Missing required query parameter: {param_name}")
    # If there are any validation errors, return a FailedRequestValidation with the error messages.
    if fail_msgs:
        if isinstance(inprocess_request, FailedRequestValidation):
            fail_msgs = list(inprocess_request.errors) + fail_msgs
        return FailedRequestValidation(
            request=request,
            errors=tuple(fail_msgs),
        )
    # Update validated fields.
    if isinstance(inprocess_request, ValidatedRequest):
        inprocess_request = deepcopy(inprocess_request)
        inprocess_request = replace(
            inprocess_request,
            query_parameters=given_query_parameters,
        )
    return inprocess_request


def _validate_body_parameters(
    request: Request,
    inprocess_request: ValidatedRequest | FailedRequestValidation,
    *,
    schema: EsiSchema,
) -> ValidatedRequest | FailedRequestValidation:
    """Validates that the body parameters provided in the request are valid for the requested operation_id according to the ESI OpenAPI schema. If any body parameters are invalid, returns a FailedRequestValidation with the appropriate error messages. If all body parameters are valid, returns the inprocess_request unchanged."""
    operation = schema.get_operation_by_id(request.operation_id)
    assert operation is not None, (
        "operation should have been found in the operation_id validation step"
    )
    expected_body_parameters = operation.request_body
    given_body_parameters = deepcopy(request.json_body)
    fail_msgs: list[str] = []
    if expected_body_parameters is None and given_body_parameters is not None:
        fail_msgs.append("Unexpected body parameters provided for this endpoint.")
    elif expected_body_parameters is not None:
        is_required = expected_body_parameters.get("required", False)
        if given_body_parameters is None:
            if is_required:
                fail_msgs.append("Missing required body parameters for this endpoint.")
        else:
            body_schema = (
                expected_body_parameters.get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            given_type = type(given_body_parameters).__name__
            if body_schema.get("type") == "object" and given_type != "dict":
                fail_msgs.append(
                    f"Invalid type for body parameters: expected object, got {given_type}"
                )
            elif body_schema.get("type") == "array" and given_type != "list":
                fail_msgs.append(
                    f"Invalid type for body parameters: expected array, got {given_type}"
                )
            else:
                # TODO see if there are any other types we need to validate here, and if
                # so add them. We would also ideally want to do more detailed validation
                # of the body parameters based on the schema, but that would require implementing
                # a full JSON schema validator, which is a non-trivial amount of work, so
                # for now we'll just do basic type validation.
                fail_msgs.append(
                    f"Unexpected request body type {given_type} or unable to validate body parameter type."
                )

    # If there are any validation errors, return a FailedRequestValidation with the error messages.
    if fail_msgs:
        if isinstance(inprocess_request, FailedRequestValidation):
            fail_msgs = list(inprocess_request.errors) + fail_msgs
        return FailedRequestValidation(
            request=request,
            errors=tuple(fail_msgs),
        )
    # Update validated fields.
    if isinstance(inprocess_request, ValidatedRequest):
        inprocess_request = deepcopy(inprocess_request)
        inprocess_request = replace(
            inprocess_request,
            json_body=given_body_parameters,
        )
    return inprocess_request


def _validate_authentication(
    request: Request,
    inprocess_request: ValidatedRequest | FailedRequestValidation,
    *,
    schema: EsiSchema,
    authorized_characters: set[int],
) -> ValidatedRequest | FailedRequestValidation:
    """Validates that the request is properly authenticated according to the requirements of the requested operation_id in the ESI OpenAPI schema. If the request is not properly authenticated, returns a FailedRequestValidation with the appropriate error message. If the request is properly authenticated, returns the inprocess_request unchanged."""
    operation = schema.get_operation_by_id(request.operation_id)
    assert operation is not None, (
        "operation should have been found in the operation_id validation step"
    )
    if operation.is_authentication_required:
        if request.authorization_id is None:
            fail_msg = f"Authentication is required for this endpoint, but no authorization_id was provided in the request."
            if isinstance(inprocess_request, FailedRequestValidation):
                fail_msgs = list(inprocess_request.errors) + [fail_msg]
            else:
                fail_msgs = [fail_msg]
            return FailedRequestValidation(
                request=request,
                errors=tuple(fail_msgs),
            )
        elif request.authorization_id not in authorized_characters:
            fail_msg = f"Authentication is required for this endpoint, but the provided authorization_id {request.authorization_id} is not in the set of authorized characters."
            if isinstance(inprocess_request, FailedRequestValidation):
                fail_msgs = list(inprocess_request.errors) + [fail_msg]
            else:
                fail_msgs = [fail_msg]
            return FailedRequestValidation(
                request=request,
                errors=tuple(fail_msgs),
            )
    # Update validated fields.
    if isinstance(inprocess_request, ValidatedRequest):
        inprocess_request = deepcopy(inprocess_request)
        inprocess_request = replace(
            inprocess_request,
            authorization_id=request.authorization_id,
        )
    return inprocess_request


def _validate_language(
    request: Request,
    inprocess_request: ValidatedRequest | FailedRequestValidation,
    *,
    schema: EsiSchema,
) -> ValidatedRequest | FailedRequestValidation:
    """Validates that the language parameter provided in the request is valid for the requested operation_id according to the ESI OpenAPI schema. If the language parameter is invalid, returns a FailedRequestValidation with the appropriate error message. If the language parameter is valid, returns the inprocess_request unchanged."""
    # check that the requested language is available from the ESI.
    available_languages = schema.content_languages
    if request.language not in available_languages:
        fail_msg = (
            f"Requested language {request.language} is not available for this endpoint."
        )
        if isinstance(inprocess_request, FailedRequestValidation):
            fail_msgs = list(inprocess_request.errors) + [fail_msg]
        else:
            fail_msgs = [fail_msg]
        return FailedRequestValidation(
            request=request,
            errors=tuple(fail_msgs),
        )
    # Update validated fields.
    if isinstance(inprocess_request, ValidatedRequest):
        inprocess_request = deepcopy(inprocess_request)
        inprocess_request = replace(
            inprocess_request,
            language=request.language,
        )
    return inprocess_request


def _set_method(
    request: Request,
    inprocess_request: ValidatedRequest | FailedRequestValidation,
    *,
    schema: EsiSchema,
) -> ValidatedRequest | FailedRequestValidation:
    """Sets the HTTP method for the request based on the requested operation_id and the ESI OpenAPI schema. If the operation_id is invalid or if there is an error determining the HTTP method, returns a FailedRequestValidation with the appropriate error message. If the HTTP method is successfully determined, returns an updated ValidatedRequest with the method field set."""
    operation = schema.get_operation_by_id(request.operation_id)
    assert operation is not None, (
        "operation should have been found in the operation_id validation step"
    )
    # Update validated fields.
    if isinstance(inprocess_request, ValidatedRequest):
        inprocess_request = deepcopy(inprocess_request)
        inprocess_request = replace(
            inprocess_request,
            method=operation.method,
        )
    return inprocess_request


def _set_url_template(
    request: Request,
    inprocess_request: ValidatedRequest | FailedRequestValidation,
    *,
    schema: EsiSchema,
) -> ValidatedRequest | FailedRequestValidation:
    """Sets the URL template for the request based on the requested operation_id and the ESI OpenAPI schema. If the operation_id is invalid or if there is an error determining the URL template, returns a FailedRequestValidation with the appropriate error message. If the URL template is successfully determined, returns an updated ValidatedRequest with the url_template field set."""
    base_url = schema.base_url
    operation = schema.get_operation_by_id(request.operation_id)
    assert operation is not None, (
        "operation should have been found in the operation_id validation step"
    )
    path_url_template = base_url + operation.path
    # Update validated fields.
    if isinstance(inprocess_request, ValidatedRequest):
        inprocess_request = deepcopy(inprocess_request)
        inprocess_request = replace(
            inprocess_request,
            path_url_template=path_url_template,
        )
    return inprocess_request


def _set_is_paged(
    request: Request,
    inprocess_request: ValidatedRequest | FailedRequestValidation,
    *,
    schema: EsiSchema,
) -> ValidatedRequest | FailedRequestValidation:
    """Determines whether the request is for a paged endpoint based on the requested operation_id and the ESI OpenAPI schema, and sets the is_paged field of the ValidatedRequest accordingly. If the operation_id is invalid or if there is an error determining whether the endpoint is paged, returns a FailedRequestValidation with the appropriate error message. If it is successfully determined whether the endpoint is paged, returns an updated ValidatedRequest with the is_paged field set."""
    # Update validated fields.
    if isinstance(inprocess_request, ValidatedRequest):
        operation = schema.get_operation_by_id(request.operation_id)
        assert operation is not None, (
            "operation should have been found in the operation_id validation step"
        )
        inprocess_request = deepcopy(inprocess_request)
        inprocess_request = replace(
            inprocess_request,
            is_paged=operation.is_paged,
        )
    return inprocess_request


def _set_is_cached(
    request: Request,
    inprocess_request: ValidatedRequest | FailedRequestValidation,
    *,
    schema: EsiSchema,
) -> ValidatedRequest | FailedRequestValidation:
    """Determines whether the request is for a cached endpoint based on the requested operation_id and the ESI OpenAPI schema, and sets the is_cached field of the ValidatedRequest accordingly. If the operation_id is invalid or if there is an error determining whether the endpoint is cached, returns a FailedRequestValidation with the appropriate error message. If it is successfully determined whether the endpoint is cached, returns an updated ValidatedRequest with the is_cached field set."""
    # Update validated fields.
    if isinstance(inprocess_request, ValidatedRequest):
        operation = schema.get_operation_by_id(request.operation_id)
        assert operation is not None, (
            "operation should have been found in the operation_id validation step"
        )
        inprocess_request = deepcopy(inprocess_request)
        inprocess_request = replace(
            inprocess_request,
            is_cached=operation.is_cached,
        )
    return inprocess_request


def _set_is_authentication_required(
    request: Request,
    inprocess_request: ValidatedRequest | FailedRequestValidation,
    *,
    schema: EsiSchema,
) -> ValidatedRequest | FailedRequestValidation:
    """Determines whether the request requires authentication based on the requested operation_id and the ESI OpenAPI schema, and sets the is_authentication_required field of the ValidatedRequest accordingly. If the operation_id is invalid or if there is an error determining whether authentication is required, returns a FailedRequestValidation with the appropriate error message. If it is successfully determined whether authentication is required, returns an updated ValidatedRequest with the is_authentication_required field set."""
    # Update validated fields.
    if isinstance(inprocess_request, ValidatedRequest):
        operation = schema.get_operation_by_id(request.operation_id)
        assert operation is not None, (
            "operation should have been found in the operation_id validation step"
        )
        inprocess_request = deepcopy(inprocess_request)
        inprocess_request = replace(
            inprocess_request,
            is_authentication_required=operation.is_authentication_required,
        )
    return inprocess_request
