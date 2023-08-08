"""
Two main goals :

- maintain a build dependency object responsible to generate bundled js files
in case of file modification
- check that dependancies are respected in the lists of files to bundle together.
"""

import collections
import json
import os.path
from pathlib import Path
import shutil
import subprocess
from typing import Union

from concat_js.settings import conf


"""
Part I :  dependancy checking in the main file.

Warning if same bundle reference same dependancy multiple times.
This ensure that a single file modification will not trigger same
bundling twice.
"""

class CycleError(Exception):
    pass

class DAG():
    # Dependancy graph. It's a directed graph where an edge mark the
    # dependency between two entities.
    # Inverse convention of orientation of edges.
    # Here, we consider file names as entities

    def __init__(self, bricks):
        # bricks is an iterable of Brick instances. See below
        self._graph = collections.defaultdict(list)
        self.get = self._graph.get
        self._roots = set()
        for brick in bricks:
            dest_path = brick.dest
            for src_path in brick.src:
                self._add_dep(src_path, dest_path)
    
    def __getitem__(self, key):
        return self._graph[key]
    
    def _add_dep(self, src, dest):
        # dest depends on src
        self[dest].append(src)
        self[src]  # create a new node if needed
        self._roots.add(dest)
    
    def _check_root(self, root, debug=False):
        # check for duplicate files in build
        # for given output file
        seen = set()
        to_check = [root]
        while len(to_check) > 0:
            node = to_check.pop()
            if node in seen:
                print("Multiple occurence of {} for bundle {}".format(
                        node, root
                    ))
                return False
            seen.add(node)
            for elt in self[node]:
                if elt not in seen:
                    to_check.append(elt)
                else:
                    print("Multiple occurence of {} for bundle {}".format(
                        elt, root
                    ))
                    return False
        return True
    
    def check(self):
        b = True
        for root in self._roots:
            b = b and self._check_root(root)
        return b
    
    def get_order(self):
        """
        Returns a topological ordering or fail with a CycleError
        """
        # using depth-first version
        # We have reverse relation compared to usual dep graphs
        L = []
        marked = set()
        temp = set()

        def visit(node):
            if node in marked or node not in self._roots:
                return
            if node in temp:
                raise CycleError(
                    "Cycling dependancy detected, containing {}".format(
                    node
                    ))
            temp.add(node)

            for t in self._graph[node]:
                visit(t)
            temp.remove(node)
            marked.add(node)
            L.append(node)
        
        for node in self._roots:
            visit(node)

        return L


"""
Part II : the bundler.

We maintain a json file containing all bundles to create. It's a list of
dicts or 2 elt lists :
- a unique name : optionnal, the first elt of the list
- a dict "dest"> path to destination, "src" : list of path to bundle.

All path strings are considered relative to conf.CONCAT_ROOT
unless a "relative_to" is given as an absolute path in a dict
"""

class Brick():
    """
    One brick to build.

    Simple wrapper around json data describing a bundle.
    """

    def __init__(self, dest="", src=tuple(), relative_to=None):
        if relative_to is None:
            relative_to = conf.CONCAT_ROOT
        else:
            relative_to = Path(relative_to.format(
                BASE_DIR=conf.BASE_DIR,
                CONCAT_ROOT=conf.CONCAT_ROOT)
            )
        self.relative_to = relative_to
        self.dest = relative_to / dest
        self.src = []
        for el in src:
            self.src.append(relative_to / el)
        

class Bundler():
    # only use absolute path as keys

    def __init__(self, printer=print):
        # delegate file loading to allow live reloading of dependancies
        self.reload()
        self.mapper = SourceMapper()
        self.printer = printer
        self.extra_files = set([conf.JSON_DEPS])
        self.lint_js = conf.LINT_COMMAND
        self.create_sourcemaps = conf.CREATE_SOURCEMAPS
    
    def reload(self, json_file : Union[Path, str]=conf.JSON_DEPS) -> None:
        self._builds = {}
        self._by_name = {}
        with open(json_file) as f:
            build_list = json.load(f)
            for elt in build_list:
                name = False
                if isinstance(elt, list):
                    # get rid of optionnal name
                    descr = elt[1]
                    name = elt[0]
                else:
                    descr = elt
                brick = Brick(**descr)
                self._builds[brick.dest] = brick
                if name is not False:
                    self._by_name = brick
            self.checker = DAG(self._builds.values())
            # Warning in case of redondant concatenation
            self.checker.check()
            # raise exception in case of cycle(s)
            self.checker.get_order()
            self.build_change_deps()

    def build_change_deps(self) -> None:
        # graph as a dict. Keys are Path instances
        self._deps = {}
        for k, v in self._builds.items():
            for key in v.src:
                current = self._deps.get(key, [])
                current.append(k)
                self._deps[key] = current
    
    def check_timestamps(self) -> None:
        """
        Check if each bundle has a last modified time at least equal
        to each of his dependancies
        """
        for build in self._builds.values():
            bundle = build.dest
            if not bundle.is_file():
                # before first build ?
                continue
            tstamp = bundle.stat().st_mtime
            for path in build.src:
                if not path.is_file():
                    self.printer("File not found : {}".format(path))
                elif path.stat().st_mtime > tstamp:
                    self.printer("Dependancy {} was modified after {}".format(
                        path.relative_to(build.relative_to),
                        bundle.relative_to(build.relative_to)
                    ))
    
    def get_rebuilds(self, changed_file: Union[Path, str]) -> list:
        """
        changed file is an absolute path
        """
        key = Path(changed_file)
        targets = self._deps.get(key, [])
        return [self._builds[k] for k in targets]
    
    def _write_bundle(self, build : Brick, out: Path) -> None:
        with open(out, "w") as bundle:
            for src in build.src:
                with open(src) as f:
                    shutil.copyfileobj(f, bundle)
                    #print("Copying {} into {}".format(relative_to / src, out))

    def _bundle_one(self, build: Brick) -> None:
        """
        Build is one of self._builds value.
        """
        # path to files to write
        out = build.dest
        # write the bundle and source map
        self.printer("Writing {}".format(build.dest))
        self._write_bundle(build, out)
        if self.create_sourcemaps:
            map_out = str(out) + ".map"
            smap = self.mapper.sourcemap(build)
            self.printer("Writing source map.") 
            with open(map_out, "w") as map_file:
                json.dump(smap, map_file)
    
    def build_by_name(self, name: str) -> bool:
        """
        Build one Bundle, gicen by it's optionnal name.
        Returns a boolean indicating if given name was found
        and bundle has been built.
        """
        if name in self._by_name:
            self._bundle_one(self._by_name[name])
            return True
        return False

    def bundle(self, changed_file: Union[Path, str]) -> None:
        # we must invalidate previous line count
        self.mapper.changed(changed_file)
        builds = self.get_rebuilds(changed_file)
        for b in builds:
            self._bundle_one(b)
            
    def file_changed(self, path: Path) -> None:
        if path in self.extra_files:
            self.printer("Main concatenation file changed.")
            self.reload()
        else:
            self.printer("{} changed, rebuild if needed".format(path.name))
            if self.lint_js and path in self._deps:
                # don't lint aftre concat.
                subprocess.run([self.lint_js, str(path)])
            self.bundle(path)
    
    def rebuild_all(self):
        # first pass, check dependancies between build files
        L = self.checker.get_order()
        for dest in L:
            self._bundle_one(self._builds[dest])
    
    def dests(self):
        """
        Iterator of all bundles file path (destination)
        """
        return self._builds.keys()


"""
Part III : sourcemaps.

Generation of a sourcemap json data for a list of files to
concatenate
"""

VLQ_BASE_SHIFT = 5

# binary: 100000
VLQ_BASE = 1 << VLQ_BASE_SHIFT

# binary: 011111
VLQ_BASE_MASK = VLQ_BASE - 1

# binary: 100000
VLQ_CONTINUATION_BIT = VLQ_BASE

VLQ_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
VLQ_NUMBERS = dict(map(reversed, enumerate(VLQ_CHARS)))

class SourceMapper():

    def __init__(self):
        # caching of file line count, since it's the only data we need
        # to compute the mappings
        self._line_count = {}
    
    def reset(self):
        # call this if the size of files may have changed
        self._line_count = {}
    
    def changed(self, abs_path):
        # a file has changed on disk. Invalidate line count
        try:
            self._line_count.pop(abs_path)
        except KeyError:
            pass

    def _vlq_encode(self, nb):
        # A single base 64 digit can contain 6 bits of data. For the base 64 variable
        # length quantities we use in the source map spec, the first bit is the sign,
        # the next four bits are the actual value, and the 6th bit is the
        # continuation bit. The continuation bit tells us whether there are more
        # digits in this value following this digit.
        #
        #   Continuation
        #   |    Sign
        #   |    |
        #   V    V
        #   101011
        res = ""
        if nb < 0:
            # this should never happen
            # set the sign bit as least significant
            nb = (-nb) << 1
            nb += 1
        else:
            # 0 as sign bit
            nb = nb << 1
        while nb > 0 or res == "": # encode 0 as well
            char = nb & VLQ_BASE_MASK
            nb = nb >> VLQ_BASE_SHIFT
            if nb > 0:
                # set continuation bit
                char = char | VLQ_CONTINUATION_BIT
            res += VLQ_CHARS[char]
        return res
    
    def _vlq_decode(self, segment):
        # see https://pvdz.ee/weblog/281
        values = []
        shift = 0 # current shift in case of continuation
        val = 0 # currently computed value
        for c in segment:
            num = VLQ_NUMBERS[c]
            continuation = num & VLQ_CONTINUATION_BIT
            num_val = num & VLQ_BASE_MASK  # base numeric value stored
            val += num_val << shift
            shift += VLQ_BASE_SHIFT 
            if not continuation:
                # end of current reading.
                # check sign to make final computation
                sign = -1 if val % 2 else 1
                val = val >> 1
                val = val * sign
                values.append(val)
                val = shift = 0
                
        return values
    
    def segment(self, file_number, line_number):
        # since we're just concatenating files,
        # Generated column will be 0 as will be original column.
        # Our fileds are : 0, file_number, line_number, 0
        return "".join(map(self._vlq_encode, [0, file_number, line_number, 0]))
    
    def mappings(self, path, prev_count=0):
        """
        Compute a mapping suitable to represent file identified by a path

        prev_count is the number of lines in previous file in concatenation

        Returns the mapping as a string and last index of line (0 based)
        for the given file.

        May not work on empty files.
        """
        if path in self._line_count:
            line_count = self._line_count[path]
        else:
            line_count = -1 # the numbering is 0 indexed
            with open(path) as f:
                for _ in f:
                    line_count += 1
            self._line_count[path] = line_count
        if prev_count: # not the first file of the concatenation
            file_nb = 1 # it's a delta in file numbering
        else:
            file_nb = 0 # no delta it's the first file
        buffer = [self.segment(file_nb, -prev_count)]
        # add line_count segments, ie one segment for each line after the first
        buffer = buffer + ["AACA"]*line_count
        return ";".join(buffer), line_count
    
    def sourcemap(self, build: Brick) -> dict:
        """
        Returns a json object as in sourcemaps specs V3.

        build is a Brick object. See above.
        """
        dest = build.dest
        smap = {
            "version": 3,
            "file": dest.name,
        }
        sources = [os.path.relpath(
            src,
            start=dest.parent) for src in build.src]
        smap["sources"] = sources
        mappings = []
        prev_count = 0
        for src in build.src:
            m, prev_count = self.mappings(
                src,
                prev_count=prev_count
            )
            mappings.append(m)
        smap["mappings"] = ";".join(mappings)
        return smap
    
    # for debugging purpose
    def extract_from_file(self, path):
        # we consider the sourmap written in the last line and base64
        # encoded, as do sourcemaps in some node/gulp setting
        with open(path) as f:
            for line in f:
                pass
            # we have the last line
            i = line.find("base64,")
            if i == -1:
                return {}
            s = line[i + 7:]
            import base64
            s = base64.b64decode(s)
            return json.loads(s)
