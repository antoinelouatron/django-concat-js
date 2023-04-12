# from contextlib import contextmanager
import json
from pathlib import Path
# import signal
import subprocess
import threading
import time



from django.test import TestCase, tag

import concat_js.settings as settings
from concat_js import dep_graph as dg
from concat_js import watch_src as ws

# class TimeoutException(Exception): pass

# @contextmanager
# def time_limit(seconds):
#     """
#     Limit execution time
#     """
#     def signal_handler(signum, frame):
#         raise TimeoutException("Timed out!")
#     signal.signal(signal.SIGALRM, signal_handler)
#     signal.alarm(seconds)
#     try:
#         yield
#     finally:
#         signal.alarm(0)

@tag("concat_js")
class TestDAG(TestCase):

    def test_brick(self):
        rel_to = Path('.').absolute()
        data = {
            #"relative_to": rel_to,
            "dest": "a.js",
            "src": [
                "src/b.js", "src/c.js"
            ]
        }
        b1 = dg.Brick(**data)
        data["relative_to"] = str(rel_to)
        b2 = dg.Brick(**data)
        self.assertEqual(len(b1.src), 2)
        self.assertEqual(len(b2.src), 2)
        self.assertEqual(b1.dest.name, b2.dest.name)
        self.assertEqual(b1.dest.parent, settings.conf.CONCAT_ROOT)
        self.assertEqual(b2.dest.parent, rel_to)

    def good_data(self):
        """
        No multiple ref nor cycle.

        3 entries
        """
        return [
            {"dest": "a.js", "src": ["src/b.js", "src/c.js"]},
            {"dest": "a2.js", "src": ["src/b2.js", "src/c.js"]},
            {"dest": "a3.js", "src": ["src/b2.js", "a.js"]},
        ]

    def test_DAG_construction(self):
        dag = dg.DAG([dg.Brick(**d) for d in self.good_data()])
        # test __getitem__
        self.assertIsInstance(dag[settings.conf.CONCAT_ROOT / "a.js"], list)
        self.assertTrue(dag.check())
        self.assertEqual(len(dag._graph), 6)
        dag.get_order()
        data = self.good_data()
        # add multiple reference to src/b.js for a.js
        data.append({"dest": "src/c.js", "src": ["src/b.js"]})
        dag = dg.DAG([dg.Brick(**d) for d in data])
        # dag._check_root(settings.CONCAT_ROOT / "a.js", debug=True)
        self.assertFalse(dag.check())
        # add a cycle
        data = self.good_data()
        data.append({"dest": "src/c.js", "src": ["a3.js"]})
        dag = dg.DAG([dg.Brick(**d) for d in data])
        self.assertFalse(dag.check())
        with self.assertRaises(dg.CycleError):
            dag.get_order()
    
    def test_cycles(self):
        base_ord = ord("A")
        for cycle_length in range(3, 11):
            # cycles of length 3-10
            data = self.good_data()
            for k in range(cycle_length):
                data.append({
                    "dest": chr(base_ord + k) + ".js",
                    "src": [chr(base_ord + (k + 1) % cycle_length) + ".js"]})
            dag = dg.DAG([dg.Brick(**d) for d in data])
            with self.assertRaises(dg.CycleError, msg="{} cycle".format(cycle_length)):
                dag.get_order()
            
    
    def test_simple_order(self):
        dag = dg.DAG([dg.Brick(**d) for d in self.good_data()])
        order = dag.get_order()
        dest_a = settings.conf.CONCAT_ROOT / "a.js"
        dest_a3 = settings.conf.CONCAT_ROOT / "a3.js"
        self.assertTrue(order.index(dest_a) < order.index(dest_a3))
    
    def test_file_order(self):
        # test with full config file
        bd = dg.Bundler()
        dag = bd.checker
        order = dag.get_order()
        test_nb = 0
        for k, v in dag._graph.items():
            for src in v:
                if src in dag._roots:
                    test_nb += 1
                    self.assertTrue(order.index(src) < order.index(k))
        print("Successfuly tested {} orderings".format(test_nb))

class TestBundler(TestCase):

    @classmethod
    def clean_build_files(cls):
        bd = dg.Bundler()
        for fpath in bd.dests():
            if fpath.is_file():
                fpath.unlink()
            smap = fpath.with_suffix(fpath.suffix + ".map")
            if smap.is_file():
                smap.unlink()

    ################################
    # Test data file is as follow
    # 3 bundles, with dests path b{i}.js with i=1,2,3
    # 4 source files src/s{i}.js
    # b3.js depends on b2.js
    ################################

    def test_init(self):
        # the json test file is concat.json
        bd = dg.Bundler()
        self.assertEqual(len(bd._builds), 3)
        for v in bd._builds.values():
            self.assertIsInstance(v, dg.Brick)
        self.assertEqual(len(bd._deps), 5)
    
    def test_deps(self):
        bd = dg.Bundler()
        rel_to = bd._builds[next(iter(bd._builds))].relative_to
        s1 = rel_to / "src/s1.js"
        rebuilds = bd.get_rebuilds(s1)
        self.assertEqual(len(rebuilds), 2)
        b2 = rel_to / "b2.js"
        self.assertIn(bd._builds[b2], rebuilds)
        self.assertEqual(len(bd.get_rebuilds(b2)), 1)
    
    def test_bundles(self):
        bd = dg.Bundler()
        bd.rebuild_all()
        for d in bd.dests():
            self.assertTrue(d.is_file())
            # no sourcemap created, see settings
            smap = d.parent / (d.name + ".map")
            self.assertFalse(smap.exists())
        path = d.parent / "b1.js"
        # test content of b1.js
        # each of its 2 sources are of length 2 exactly
        with open(path) as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 4)
        # test b3.js with contains 4 (b2.js) + 2 lines
        path = d.parent / "b3.js"
        with open(path) as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 6)
    
    def test_timestamps(self):
        # self.clean_build_files()
        L = []
        def printer(msg):
            L.append(msg)
        bd = dg.Bundler(printer=printer)
        bd.check_timestamps()
        self.assertEqual(len(L), 0)
        
    
    @classmethod
    def tearDownClass(cls) -> None:
        cls.clean_build_files()
        

class TestSourcemaps(TestCase):


    def test_content(self):
        bd = dg.Bundler()
        bd.create_sourcemaps = True
        bd.rebuild_all()
        for dest in bd.dests():
            smap = Path(str(dest) + ".map")
            self.assertTrue(smap.is_file())
        smap = dest.parent / "b1.js.map"
        with open(smap) as f:
            data = json.load(f)
            self.assertEqual(data["version"], 3)
            self.assertEqual(data["file"], "b1.js")
            self.assertEqual(len(data["sources"]), 2)
            segments = data["mappings"].split(";")
            self.assertEqual(len(segments), 4)
            smapper = dg.SourceMapper()
            decoded = [smapper._vlq_decode(s) for s in segments]
            for i, d in enumerate(decoded):
                self.assertEqual(len(d), 4)
                #column number
                self.assertEqual(d[0], 0)
                # file delta : 1 only for third element
                self.assertEqual(d[1], int(i==2))
                # line delta should be 0, 1, -1, 1
                deltas = [0, 1, -1, 1]
                self.assertEqual(d[2], deltas[i])
                # column number
                self.assertEqual(d[3], 0)
        
        smap = dest.parent / "b3.js.map"
        with open(smap) as f:
            data = json.load(f)
            segments = data["mappings"].split(";")
            self.assertEqual(len(segments), 6)
    
    @classmethod
    def tearDownClass(cls) -> None:
        TestBundler.clean_build_files()

class TestWatcher(TestCase):
    
    def test_thread(self):
        watcher = ws.JsWatcher()
        thread = threading.Thread(target=watcher.run)
        thread.start()
        watcher.stop()
        thread.join(timeout=1)
        self.assertFalse(thread.is_alive())
    
    def test_file_changed(self):
        # dummy receiver
        class Receiver():
            def __init__(self):
                self.changed = []
            def file_changed(self, arg):
                self.changed.append(arg)
        
        watcher = ws.JsWatcher()
        receiver = Receiver()
        watcher.register(receiver)
        thread = threading.Thread(target=watcher.run)
        thread.start()
        bd = dg.Bundler()
        sources = list(bd._deps.keys())
        with open(sources[0]) as f:
            orig_content = f.read()
        with open(sources[0], "w") as f:
            f.write("Un truc")
        time.sleep(0.2)
        with open(sources[0], "w") as f:
            f.write(orig_content)
        # some sleep to let changes propagate.
        time.sleep(0.2)
        watcher.stop()
        thread.join(timeout=1)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(receiver.changed), 2)
    
    def test_command(self):
        # the django management command
        subprocess.run(
            ["python",
            "{}".format(Path(".") / "concat_js/test_app/manage.py"),
            "watch_js",
            "--rebuild"],
            timeout=1
        )
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run(
            ["python",
            "{}".format(Path(".") / "concat_js/test_app/manage.py"),
            "watch_js"],
            timeout=1
            )
    
    @classmethod
    def tearDownClass(cls) -> None:
        TestBundler.clean_build_files()
        
