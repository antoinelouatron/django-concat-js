import logging
from pathlib import Path
# import time
from typing import Union, Iterator

import watchfiles

# from django.utils import autoreload
# from django.conf import settings

# import pywatchman

logger = logging.getLogger("core.watch_js")

# class JsWatcher(autoreload.WatchmanReloader):
#     """
#     See base implementation. We get rid of django reloading code.
#     """

#     def __init__(self, bundler):
#         super().__init__()
#         bd = Path(settings.BASE_DIR) / "static" / "js"
#         self.directory_globs = {
#             bd / "src": ("**/*.js",),
#             bd / "build" : ("**/*.js",)
#         }
#         self.bundler = bundler
#         self.extra_files.update(bundler.extra_files)

#     def notify_file_changed(self, path: Union[str, Path]) -> None:
#         # no more signal
#         self.bundler.file_changed(path)
    
#     def _tick_once(self):
#         if self.processed_request.is_set():
#             # TODO change condition to update watches
#             self.update_watches()
#             self.processed_request.clear()
#         try:
#             self.client.receive()
#         except pywatchman.SocketTimeout:
#             pass
#         except pywatchman.WatchmanError as ex:
#             logger.debug("Watchman error: %s, checking server status.", ex)
#             self.check_server_status(ex)
#         else:
#             for sub in list(self.client.subs.keys()):
#                 self._check_subscription(sub)

#     def tick(self):
#         # remove the signal connection
#         self.update_watches()
#         while True:
#             self._tick_once()
#             yield
#             # Protect against busy loops.
#             time.sleep(0.1)
    
#     def watched_files(self, include_globs: bool = True) -> Iterator[Path]:
#         yield from self.extra_files
#         if include_globs:
#             for directory, patterns in self.directory_globs.items():
#                 for pattern in patterns:
#                     yield from directory.glob(pattern)
