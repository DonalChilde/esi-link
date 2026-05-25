# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pyyaml>=6.0.3",
# ]
# ///

import json

from yaml import safe_dump


def json_to_yaml(json_string: str, indent: int = 2) -> str:
    """Convert a JSON string to a YAML string.

    Args:
        json_string (str): The input JSON string.
        indent (int): The number of spaces to use for indentation in the YAML output.

    Returns:
        str: The converted YAML string.
    """
    # Parse the JSON string into a Python object
    data = json.loads(json_string)
    # Convert the Python object to a YAML string
    yaml_string = safe_dump(data, sort_keys=False, indent=indent)
    return yaml_string


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Convert JSON to YAML.")
    parser.add_argument(
        "infile",
        nargs="?",
        default=None,
        help="input file or '-' for stdin (default: stdin)",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=None,
        help="The output YAML file to save the converted result to (default: stdout)",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="The number of spaces to use for indentation in the YAML output (default: %(default)s)",
    )
    args = parser.parse_args()

    # Read JSON input, either from file or stdin ('-' means stdin)
    if args.infile and args.infile != "-":
        input_path = Path(args.infile)
        with input_path.open("r", encoding="utf-8") as f:
            json_input = f.read()
    else:
        json_input = sys.stdin.read()

    # Convert JSON to YAML
    yaml_output = json_to_yaml(json_input, indent=args.indent)

    # Write YAML output, either to file or stdout
    if args.output_file:
        output_path = args.output_file
        with output_path.open("w", encoding="utf-8") as f:
            # yaml dumper already adds a newline at the end, so we don't need to add another one
            f.write(yaml_output)

        print(f"Converted YAML saved to {output_path.resolve()}")
    else:
        # yaml dumper already adds a newline at the end, so we don't need to add another one
        print(yaml_output, end="")
