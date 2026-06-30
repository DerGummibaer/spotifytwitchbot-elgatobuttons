"""
Updates the version number in both spotify-service/version.py and
spotify-service/version.ini, so the two files can never drift out of
sync -- called by rebuild-all.bat, not meant to be run directly.

Usage: python set-version.py 1.2.0
"""
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print("Usage: python set-version.py <version>")
    sys.exit(1)

new_version = sys.argv[1].strip()

# Basic sanity check -- not strict semver enforcement, just catches
# obvious typos like forgetting to actually type a version number.
if not re.match(r"^\d+\.\d+\.\d+$", new_version):
    print(f"'{new_version}' doesn't look like a version number (expected something like 1.2.0).")
    sys.exit(1)

root = Path(__file__).parent
version_py = root / "spotify service" / "version.py"
version_ini = root / "spotify service" / "version.ini"

if not version_py.exists():
    print(f"Could not find {version_py}")
    sys.exit(1)
if not version_ini.exists():
    print(f"Could not find {version_ini}")
    sys.exit(1)

# version.py: replace the VERSION = "..." line, wherever it appears,
# leaving every comment line untouched.
py_content = version_py.read_text(encoding="utf-8")
py_content_new, count = re.subn(
    r'VERSION\s*=\s*"[^"]*"',
    f'VERSION = "{new_version}"',
    py_content,
)
if count == 0:
    print(f"Could not find a VERSION = \"...\" line in {version_py}")
    sys.exit(1)
version_py.write_text(py_content_new, encoding="utf-8")
print(f"  version.py  -> VERSION = \"{new_version}\"")

# version.ini: replace the Number=... line under [Version].
ini_content = version_ini.read_text(encoding="utf-8")
ini_content_new, count = re.subn(
    r'Number\s*=\s*\S*',
    f'Number={new_version}',
    ini_content,
)
if count == 0:
    print(f"Could not find a Number=... line in {version_ini}")
    sys.exit(1)
version_ini.write_text(ini_content_new, encoding="utf-8")
print(f"  version.ini -> Number={new_version}")
