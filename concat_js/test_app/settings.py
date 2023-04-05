from pathlib import Path
from settings_base import *

CONCAT_JS = {
    "CONCAT_ROOT": BASE_DIR / "test_app" /"static/",
    "JSON_DEPS": BASE_DIR / "test_app/concat.json",
    "CREATE_SOURCEMAPS": False,
    "LINT_COMMAND": False,
    "FILTER_EXTS": (".js", )
}