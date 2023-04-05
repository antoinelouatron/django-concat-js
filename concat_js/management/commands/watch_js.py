import subprocess

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help_text="Surveillance des fichier js et auto-concaténation"


    def handle(self, *args, **kwargs):
        from concat_js import watch_src, dep_graph, settings
        bundler = dep_graph.Bundler(printer=self.stdout.write)
        if bundler.lint_js:
            self.stdout.write("Linting js files")
            # TODO : change base dir to lint
            subprocess.run([bundler.lint_js, "static/js/src/"])
        self.stdout.write("Watching for js file changes.")
        try:
            bundler.check_timestamps()
            watcher = watch_src.JsWatcher()
            watcher.register(bundler)
            watcher.run()
        except KeyboardInterrupt:
            watcher.stop()
            self.stdout.write("")