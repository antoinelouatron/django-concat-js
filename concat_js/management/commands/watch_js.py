import subprocess

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help_text="Watch for file changes and concatenate when needed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--rebuild",
            action="store_true",
            help="Only rebuild all bundle and exit."
        )
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--maps",
            action="store_true",
            help="Override CRETE_SOURCEMAPS settings for this run."
        )
        group.add_argument(
            "--no-maps",
            action="store_true",
            help="Override CRETE_SOURCEMAPS settings for this run."
        )


    def handle(self, *args, **options):
        from concat_js import watch_src, dep_graph
        from concat_js.settings import conf
        bundler = dep_graph.Bundler(printer=self.stdout.write)
        if options["maps"]:
            bundler.create_sourcemaps = True
        elif options["no_maps"]:
            bundler.create_sourcemaps = False
        if conf.LINT_BASE:
            self.stdout.write("Linting files in {}.".format(conf.LINT_BASE))
            subprocess.run([bundler.lint_js, conf.LINT_BASE])
        if options["rebuild"]:
            self.stdout.write("Rebuild all bundles.")
            bundler.rebuild_all()
            return
        self.stdout.write("Watching for file changes.")
        try:
            bundler.check_timestamps()
            watcher = watch_src.JsWatcher()
            watcher.register(bundler)
            watcher.run()
        except KeyboardInterrupt:
            watcher.stop()
            self.stdout.write("")