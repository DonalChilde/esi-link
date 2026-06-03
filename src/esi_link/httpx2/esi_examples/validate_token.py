# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "httpx2>=2.0.0",
#     "pyjwt[crypto]>=2.12.1",
#     "whenever>=0.10.0",
# ]
#
# [tool.uv]
# exclude-newer = "7 days"
# ///

import argparse
import json
import logging
import sys
from pathlib import Path

from jwt import PyJWKClient

from esi_examples.helpers.oauth_tokens import validate_jwt_token

logger = logging.getLogger(__name__)

JWKS_URI = "https://login.eveonline.com/oauth/jwks"
"""The URL to fetch the JSON Web Key Set (JWKS) for validating JWT tokens."""
AUDIENCE = "EVE Online"
"""The expected audience for the JWT tokens."""
ISSUER = "https://login.eveonline.com"
"""The expected issuer for the JWT tokens."""
USER_AGENT = "ESI Token Validator/1.0"
"""The User-Agent string to use in requests."""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate a JWT token.")
    parser.add_argument(
        "infile",
        nargs="?",
        default=None,
        help="input file or '-' for stdin (default: stdin)",
    )
    parser.add_argument(
        "--jwks-uri",
        type=str,
        default=JWKS_URI,
        help="The URL to fetch the JSON Web Key Set (JWKS) for validating JWT tokens (default: %(default)s)",
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

    pwks_client = PyJWKClient(
        args.jwks_uri, headers={"User-Agent": "ESI Token Validator/1.0"}
    )
    token_data = json.loads(json_input)
    validated_token = validate_jwt_token(
        access_token=token_data["access_token"],
        jwks_client=pwks_client,
        audience=AUDIENCE,
        issuers=[ISSUER],
        user_agent=USER_AGENT,
    )

    # Write the validated token output, either to file or stdout
    if args.output_file:
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(validated_token, f, indent=args.indent)

        print(f"Validated token saved to {output_path.resolve()}")
    else:
        print(json.dumps(validated_token, indent=args.indent), end="")
