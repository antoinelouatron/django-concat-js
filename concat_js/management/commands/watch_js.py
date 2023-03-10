import subprocess

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help_text="Surveillance des fichier js et auto-concaténation"


    def handle(self, *args, **kwargs):
        from concat_js import watch_src, dep_graph
        bundler = dep_graph.Bundler(printer=self.stdout.write)
        if bundler.lint_js:
            self.stdout.write("Linting js files")
            subprocess.run(["jshint", "static/js/src/"])
        self.stdout.write("Watching for js file changes.")
        try:
            bundler.check_timestamps()
            watcher = watch_src.JsWatcher(bundler)
            watcher.run_loop()
        except KeyboardInterrupt:
            self.stdout.write("")