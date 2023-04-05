from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class Conf():

    def __init__(self):
        try:
            self.conf = settings.CONCAT_JS
        except:
            raise ImproperlyConfigured("No CONCAT_JS setting found")
        self.set_defaults()
    
    def set_defaults(self):
        # copy all settings
        for k, v in self.conf.items():
            if k == "conf" or k == "set_defaults":
                raise ImproperlyConfigured("Invalid setting name CONCAT_JS['{}']".format(k))
            setattr(self, k, v)
        # check default values
        self.CONCAT_ROOT = Path(self.conf.get("CONCAT_ROOT")) or settings.BASE_DIR
        self.JSON_DEPS = Path(self.conf.get("JSON_DEPS"))
        if self.JSON_DEPS is None:
            raise ImproperlyConfigured("No JSON_DEPS settings defined")
        self.LINT_COMMAND = self.conf.get("LINT_COMMAND", False)
        self.FILTER_EXTS = self.conf.get("FILTER_EXTS", (".js",))
        # copy BASE_DIR
        self.BASE_DIR = settings.BASE_DIR
        self.CREATE_SOURCEMAPS = self.conf.get("CREATE_SOURCEMAPS", False)
    
    def get(self, key, default=None):
        return self.conf.get(key, default)


conf = Conf()



