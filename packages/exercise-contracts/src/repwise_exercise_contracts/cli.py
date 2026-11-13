from __future__ import annotations

import argparse
import json
from pathlib import Path

from .validation import ContractValidationError, validate_contract


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate RepWise exercise contracts")
    parser.add_argument("contracts", nargs="+", type=Path)
    args = parser.parse_args()
    failed = False
    for path in args.contracts:
        try:
            validate_contract(json.loads(path.read_text(encoding="utf-8")))
        except (ContractValidationError, json.JSONDecodeError) as error:
            failed = True
            print(f"INVALID {path}\n{error}")
        else:
            print(f"VALID {path}")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
