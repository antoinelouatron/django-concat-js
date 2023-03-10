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
        self.CONCAT_ROOT = self.conf.get("CONCAT_ROOT") or settings.BASE_DIR
        self.JSON_DEPS = self.conf.get("JSON_DEPS")
        if self.JSON_DEPS is None:
            raise ImproperlyConfigured("No JSON_DEPS settings defined")
        self.LINT_JS = self.conf.get("LINT_JS", False)
        # copy BASE_DIR
        self.BASE_DIR = settings.BASE_DIR


conf = Conf()



