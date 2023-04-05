import subprocess

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help_text="Surveillance des fichier js et auto-concaténation"


    def handle(self, *args, **kwargs):
        from concat_js import watch_src, dep_graph, settings
        bundler = dep_graph.Bundler(printer=self.stdout.write)
        if settings.LINT_BASE:
            self.stdout.write("Linting files in {}.".format(settings.LINT_BASE))
            subprocess.run([bundler.lint_js, settings.LINT_BASE])
        self.stdout.write("Watching for file changes.")
        try:
            bundler.check_timestamps()
            watcher = watch_src.JsWatcher()
            watcher.register(bundler)
            watcher.run()
        except KeyboardInterrupt:
            watcher.stop()
            self.stdout.write("")