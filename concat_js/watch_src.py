import functools
import logging
from pathlib import Path
import threading
from typing import Sequence, Union

import watchfiles

from concat_js.settings import conf
# from django.utils import autoreload
# from django.conf import settings

# import pywatchman

logger = logging.getLogger("core.watch_js")

# copied from django.utils.autoreload
@functools.lru_cache(maxsize=1)
def common_roots(paths):
    """
    Return a tuple of common roots that are shared between the given paths.
    File system watchers operate on directories and aren't cheap to create.
    Try to find the minimum set of directories to watch that encompass all of
    the files that need to be watched.
    """
    # Inspired from Werkzeug:
    # https://github.com/pallets/werkzeug/blob/7477be2853df70a022d9613e765581b9411c3c39/werkzeug/_reloader.py
    # Create a sorted list of the path components, longest first.
    path_parts = sorted([x.parts for x in paths], key=len, reverse=True)
    tree = {}
    for chunks in path_parts:
        node = tree
        # Add each part of the path to the tree.
        for chunk in chunks:
            node = node.setdefault(chunk, {})
        # Clear the last leaf in the tree.
        node.clear()

    # Turn the tree into a list of Path instances.
    def _walk(node, path):
        for prefix, child in node.items():
            yield from _walk(child, path + (prefix,))
        if not node:
            yield Path(*path)

    return tuple(_walk(tree, ()))

class ConcatFilter(watchfiles.DefaultFilter):

    def __init__(self,
            extensions: Sequence[str],
            extras: Sequence[Union[Path, str]]=tuple()) -> None:
        """
        If extensions is non empty, the filter result will be True only
        for files with one of given file extension(s).

        If extras if not empty, the given path will always be retained.
        This takes precedence over the extensions parameter.
        """
        self.extensions = extensions
        self.extras = extras
        super().__init__()
    
    def __call__(self, change: watchfiles.Change, path: str) -> bool:
        path_obj = Path(path)
        if path_obj in self.extras:
            return True
        b = not path_obj.is_dir()
        if self.extensions:
            b = b and (path_obj.suffix in self.extensions)
        return b and super().__call__(change, path)
    

class JsWatcher():

    def __init__(self):
        self.exts = conf.FILTER_EXTS
        self.watched_dirs = conf.get("WATCHED_DIRS", [conf.CONCAT_ROOT])
        self.watched_dirs = tuple(self.watched_dirs)
        self.extra_files = set()
        self.notify = []  # instances to notify for file changes
        # via file_changed(file_path)
        self._stop_event = threading.Event()
    
    def register(self, inst):
        self.notify.append(inst)
    
    def stop(self):
        self._stop_event.set()
    
    def run(self):
        # first add extra for each receivers
        for inst in self.notify:
            if hasattr(inst, "extra_files"):
                for fpath in inst.extra_files:
                    self.extra_files.add(fpath)
        roots = common_roots(self.watched_dirs + tuple(self.extra_files))
        filter = ConcatFilter(self.exts, self.extra_files)
        for changes in watchfiles.watch(
            *roots,
            watch_filter=filter,
            raise_interrupt=False,
            stop_event=self._stop_event):
            for change in changes:
                if change[0] == watchfiles.Change.modified:
                    for inst in self.notify:
                        inst.file_changed(Path(change[1]))
        # stoped by keyboardInterrupt, nothing to worry about
        return True
                

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
