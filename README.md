# Concat JS

[![PyPI - Version](https://img.shields.io/pypi/v/concat-js.svg)](https://pypi.org/project/concat-js)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/concat-js.svg)](https://pypi.org/project/concat-js)

-----

**Table of Contents**

- [Use case](#usecase)
- [Installation](#installation)
- [Settings](#settings)
- [Usage](#usage)
- [License](#license)

## Use case
This small app aim to provide automatic concatenation of javascript (or any other file) files.
Typical use case is to combine sets of small js files and bundle then into one functionnal script for each «web page», and reduce the overhead of multiple web requests.

## Installation

First of all install the app from PyPi
```console
pip install django-concat-js
```

After installing the package, add `concat_js` in in your `INSTALLED_APPS` settings

```python
INSTALLED_APPS = (
    ...
    'concat_js',
)
```

## Settings

You need to configure the app before using it. It's done by adding a setting in your `settings.py` file

```python
CONCAT_JS = {
    "JSON_DEPS": a Path to main JSON file,
    "CONCAT_ROOT": a Path,
    "CREATE_SOURCEMAPS": False,
    "LINT_COMMAND": False,
    "FILTER_EXTS": ("js", )
}
```

The main setting here is `JSON_DEP` which should point to a JSON file. It can be a `Path` or a string.
This files contains a list of objects with following attributes
```JSON
{
	"relative_to": "{BASE_DIR}/my_path/",
	"dest": "first_destination.js",
	"src": [
	    "src/first_source.js",
	    "src/second_source.js"
	]
}
```

- `relative_to` is an optionnal string containing an absolute path to a directory. All other path in this object are considered relative to this directory. Defaults to `CONCAT_ROOT` (see below). You can use `BASE_DIR` (defined in django default `settings.py` file) or `CONCAT_ROOT` as format placeholder.
- `src` is a list of relative path to files to be concatenated. The result is in....
- `dest` is the relative path to the concatenated file.

If you want to, you can name each bundle and use the more verbose 
```JSON
[
	"my_wonderful_name",
	bundle_spec
]
```
where `bundle_spec` is an object described above.

### Other settings

- `CONCAT_ROOT` is a `Path` or string setting. See aboce for meaning. It defaults to `BASE_DIR`
- `CREATE_SOURCEMAP` is a boolean, which defaults to `False`. If `True`, each bundling will also create a sourcemap file named `{dest}.map`
- `LINT_COMMAND` must be `False` or a string used to invoke a linter in current environment.
- `FILTER_EXTS` is an iterable of extension strings which defaults to the tuple `(".js", )`. Only files with given extensions will be watched for changes.


## Usage

Once configured, you can watch for changed files with

```python
python manage.py watch_js
```

## License

`concat-js` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
