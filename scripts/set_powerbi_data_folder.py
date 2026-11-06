#!/usr/bin/env python3
"""Utility to configure the DataFolder parameter in desktop_build generated project.

Usage:
    python scripts/set_powerbi_data_folder.py [path_to_data_folder]

If no path is provided, it auto-detects the repository's powerbi/desktop_build/data/ folder.
"""

import sys
import re
from pathlib import Path

def set_data_folder(custom_path=None):
    root = Path(__file__).resolve().parents[1]
    expressions_file = root / "powerbi" / "desktop_build" / "generated" / "BusinessPulse.SemanticModel" / "definition" / "expressions.tmdl"
    
    if not expressions_file.is_file():
        print(f"Error: expressions file not found at {expressions_file}")
        sys.exit(1)
        
    if custom_path:
        folder = str(custom_path)
    else:
        folder = str((root / "powerbi" / "desktop_build" / "data").resolve())
        
    if not folder.endswith("\\") and not folder.endswith("/"):
        folder += "\\"
        
    content = expressions_file.read_text(encoding="utf-8")
    new_param = f'"{folder}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]'
    updated = re.sub(
        r'(?m)^expression DataFolder =\s*\n\s*".*?"\s*meta\s*\[IsParameterQuery\s*=\s*true,.*?\]\s*$',
        f"expression DataFolder =\n    {new_param}",
        content
    )
    
    expressions_file.write_text(updated, encoding="utf-8")
    print(f"Successfully updated DataFolder parameter to:\n  {folder}")

if __name__ == "__main__":
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    set_data_folder(path_arg)
