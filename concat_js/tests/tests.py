from pathlib import Path

from django.test import TestCase, tag

import concat_js.settings as settings
from concat_js import dep_graph as dg
from concat_js import watch_src as ws

@tag("concat_js")
class TestDAG(TestCase):

    def testBrick(self):
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

    def testDAGConstruction(self):
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
    
    def testCycles(self):
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
            
    
    def testSimpleOrder(self):
        dag = dg.DAG([dg.Brick(**d) for d in self.good_data()])
        order = dag.get_order()
        dest_a = settings.conf.CONCAT_ROOT / "a.js"
        dest_a3 = settings.conf.CONCAT_ROOT / "a3.js"
        self.assertTrue(order.index(dest_a) < order.index(dest_a3))
    
    def testFileOrder(self):
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


# class TestWatcher(TestCase):

#     def test_available(self):
#         bd = dg.Bundler()
#         watcher = ws.JsWatcher(bd)
#         self.assertIsNone(watcher._tick_once())
