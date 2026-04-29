---
description: "Python coding conventions and guidelines"
applyTo: "**/*.py"
---

# Python Coding Conventions

## Python Instructions

- Write clear and concise comments for each function.
- Ensure functions have descriptive names and include type hints.
- Provide docstrings following PEP 257 conventions.
- Break down complex functions into smaller, more manageable functions.
- During development, use the virtual environment found at the project root - `./.venv`
- all code should be typed. eg. `foo:list[int] = [1,2,3]`
- use red/green TDD

## General Instructions

- Always prioritize readability and clarity.
- For algorithm-related code, include explanations of the approach used.
- Write code with good maintainability practices, including comments on why certain design decisions were made.
- Handle edge cases and write clear exception handling.
- For libraries or external dependencies, mention their usage and purpose in comments.
- Use consistent naming conventions and follow language-specific best practices.
- Write concise, efficient, and idiomatic code that is also easily understandable.

## Code Style and Formatting

- Follow the **PEP 8** style guide for Python.
- Maintain proper indentation (use 4 spaces for each level of indentation).
- Prefer lines do not exceed 88 characters.
- Use blank lines to separate functions, classes, and code blocks where appropriate.
- Code will be formatted and linted using ruff. The configuration is located in the `pyproject.toml`.
- Calls to functions with more than one argument should prefer keyword args.

## Edge Cases and Testing

- Always include test cases for critical paths of the application.
- Account for common edge cases like empty inputs, invalid data types, and large datasets.
- Include comments for edge cases and the expected behavior in those cases.
- Write unit tests for functions and document them with docstrings explaining the test cases.

## Testing

- Use pytest for testing
- Run tests: `pytest`
- Run with coverage: `pytest --cov`

## Documentation

- Ensure all public functions and classes have appropriate docstrings.
- Use Google style docstrings for consistency.
- Include examples in docstrings where applicable.
- Classes with an `__init__` function should have the docstring after that `__init__` function.
- Classes without an `__init__` function should have the docstring immediately following the class definition.

## Project Structure

- `src/esi_link/` - Main package code
- `tests/` - Test suite mirroring src structure
- `src/esi_link/cli/` - Command-line interface using Typer
- `src/esi_link/helpers/` - Utility functions

## Dependencies

- aiohttp - Async HTTP requests to ESI API
- aiolimiter - Rate limiting for API calls
- pydantic - Data validation and settings management
- pydantic-settings - Settings management for the CLI
- typer - CLI framework
- whenever - Date/time handling
- esi-auth - Managing authentication tokens for the EVE Esi.
- eve-static-data - Managing EVE Online SDE data.

## Development Commands

- Format code: `ruff format`
- Lint code: `ruff check`
- Run CLI: `esi-link [command]`

## Project Description

esi-link is a cli-focused front end to the EVE Online ESI api.

Some features are:

- The ability to create repeatable requests, allowing for quickly updating commonly used information.
- Easy aquisition of authentication tokens for auth required requests.
- Async network requests based on aiohttp.
- User configurable rate limiting based on requests per second. (Some restrictions apply.)
- File based caching to reduce network load, and respect ESI best practices.
- User configurable response handlers for the downloaded data. Easily save the responses as json data with custom file names.
- A plug-in system for user-created response handlers (Not yet implemented)
- An API to allow for use by a third party program (Not yet implemented.)
