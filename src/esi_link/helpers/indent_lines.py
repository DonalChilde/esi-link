def indent_lines(text: str, indent: int = 4) -> str:
    """Indent each line of the given text by the specified number of spaces."""
    indentation = " " * indent
    return "\n".join(
        f"{indentation}{line}" if line.strip() else line for line in text.splitlines()
    )
