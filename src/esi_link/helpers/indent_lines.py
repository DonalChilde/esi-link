def indent_lines(text: str, indent: int = 4) -> str:
    """Indent each line of the given text by the specified number of spaces."""
    indentation = " " * indent
    return "\n".join(
        f"{indentation}{line}" if line.strip() else line for line in text.splitlines()
    )


def prefixed_list_to_lines(
    items: list[str], prefix: str = "- ", indent: int = 4
) -> str:
    """Create a list with each item prefixed and indented."""
    indentation = " " * indent
    return "\n".join(f"{indentation}{prefix}{item}" for item in items)


def indented_list_to_lines(items: list[str], indent: int = 4) -> str:
    """Create an indented list from the given items."""
    indentation = " " * indent
    return "\n".join(f"{indentation}- {item}" for item in items)
