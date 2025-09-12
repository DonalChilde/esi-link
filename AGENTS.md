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

## Edge Cases and Testing

- Always include test cases for critical paths of the application.
- Account for common edge cases like empty inputs, invalid data types, and large datasets.
- Include comments for edge cases and the expected behavior in those cases.
- Write unit tests for functions and document them with docstrings explaining the test cases.

## Documentation

- Ensure all public functions and classes have appropriate docstrings.
- Use Google style docstrings for consistency.
- Include examples in docstrings where applicable.
- Classes with an `__init__` function should have the docstring after that `__init__` function.
- Classes without an `__init__` function should have the docstring immediately following the class definition.
