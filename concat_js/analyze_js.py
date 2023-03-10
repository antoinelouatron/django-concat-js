import collections
import os
from pathlib import Path
import re

"""
Part I : dep checking. We assume each js file has a unique name.

TODO : allow dotted names to qualify file names.

Search for require : (*.js)+ in begining of each js files

Convention : a js file with requirement begins with :
/**
 * [line]*
 * require : file1.js[, file.js]
 * [line]*
 */
"""

class DepNode():
    """
    Représente un noeud de l'arbre de dépendance.

    ie. un fichier dont les fils sont les dépendances.
    """

    def __init__(self, name, full_path="", edges=None):
        """
        Arguments.

        name est le nom court à afficher
        full_path est le chemin vers le fichier
        edges est une liste optionnelle de noeud fils à ajouter à la création.
        """
        self.name = name
        self.full_path = full_path
        self._edges = []
        if edges is not None:
            self.add_edges(*edges)

    def add_edges(self, *edges):
        """Ajout d'un ou plusieurs noeud fils, les dépendances pour ce fichier."""
        self._edges.extend(edges)
        return self

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    def get_deps(self):

        def _get_deps_rec(node, resolved, seen):
            seen.append(node)
            for edge in node._edges:
                if edge not in resolved:
                    if edge in seen:
                        raise Exception(
                            'Circular reference detected: %s -> %s' % (node.name, edge.name)
                        )
                    _get_deps_rec(edge, resolved, seen)
            resolved.append(node)

        resolved = []
        _get_deps_rec(self, resolved, [])
        return resolved

    def flatten(self):
        seen = set()
        res = []
        for edge in self._edges:
            flat = edge.flatten()
            for e in flat:
                if e not in seen:
                    res.append(e)
                    seen.add(e)
            if edge not in seen:
                seen.add(edge)
                res.append(edge)
        return res


class DepGraph(dict):
    """Special case of defaultdict."""

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            node = DepNode(key)
            self[key] = node
            return node


class JsDep():

    jspattern = re.compile(".*\.js")

    def __init__(self, basedir="static/js/src/"):
        self._deps = DepGraph()
        self._init_locations(basedir)

    def _init_locations(self, dirname):
        self._locations = collections.defaultdict(list)
        for d, subsidrs, files in os.walk(dirname):
            for fname in files:
                if self.jspattern.match(fname):
                    self._locations[fname].append(os.path.join(d, fname))
                    if len(self._locations[fname]) > 1:
                        print("Attention, plusieurs fichiers du nom de {}".format(
                            fname
                        ))
                        print(*self._locations[fname], sep="\n")

    def analyze(self, dirname):
        for d, subsidrs, files in os.walk(dirname):
            for fname in files:
                if self.jspattern.match(fname):
                    self._analyze_file(Path(d, fname))
        return self._deps

    def _analyze_file(self, fname):
        with open(str(fname)) as f:
            for line in f:
                l = line.strip()
                if l.startswith("/*"):
                    continue
                elif l.startswith("*"):
                    # a good candidate
                    l = l.strip("*").strip()
                    if l.startswith("require"):
                        deps = self._get_deps(l)
                        node = self._deps[fname.name]
                        node.full_path = str(fname)
                        node.add_edges(*deps)
                else:
                    break

    def _get_deps(self, l):
        """
        the line l contains deps list, comma separated.
        """
        l = l[7:].strip().strip(":")  # if we get there, l begins by "require"
        # get rid of :
        deps = [self._deps[s.strip()] for s in l.split(",")]
        for d in deps:
            L = self._locations[d.name]
            d.full_path = L[0]
            if len(L) > 1:
                print("Attention, plusieurs chemins pour {}".format(d.name))
        return deps
