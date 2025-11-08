# this is a hack to monkey patch pytest so it handles tests inside namespace packages without __init__.py properly
# without it, pytest can't discover the package root for some reason
# also see https://github.com/karlicoss/pytest_namespace_pkgs for more

import os
import pathlib
from typing import Optional

import _pytest.main
import _pytest.pathlib

# Get the project root directory (where tox.ini, pyproject.toml live)
# conftest.py is in tests/, so we need to go up one level to get to project root
conftest_path = pathlib.Path(__file__).absolute()
project_root = conftest_path.parent.parent.resolve()
src_dir = project_root / 'src'

assert src_dir.exists(), f"Expected src directory at {src_dir}, but it doesn't exist. Project root: {project_root}"

# TODO assert it contains package name?? maybe get it via setuptools..

namespace_pkg_dirs = [str(d) for d in src_dir.iterdir() if d.is_dir()]

# resolve_package_path is called from _pytest.pathlib.import_path
# takes a full abs path to the test file and needs to return the path to the 'root' package on the filesystem
resolve_pkg_path_orig = _pytest.pathlib.resolve_package_path


def resolve_package_path(path: pathlib.Path) -> Optional[pathlib.Path]:
    result = path  # search from the test file upwards
    for parent in result.parents:
        if str(parent) in namespace_pkg_dirs:
            return parent
    if os.name == 'nt':
        # ??? for some reason on windows it is trying to call this against conftest? but not on linux/osx
        if path.name == 'conftest.py':
            return resolve_pkg_path_orig(path)
    raise RuntimeError(f"Couldn't determine path for {path}")


# NOTE: seems like it's not necessary anymore?
# keeping it for now just in case
# after https://github.com/pytest-dev/pytest/pull/13426 we should be able to remove the whole conftest
# _pytest.pathlib.resolve_package_path = resolve_package_path


# without patching, the orig function returns just a package name for some reason
# (I think it's used as a sort of fallback)
# so we need to point it at the absolute path properly
# not sure what are the consequences.. maybe it wouldn't be able to run against installed packages? not sure..
search_pypath_orig = _pytest.main.search_pypath


def search_pypath(module_name: str) -> str:
    mpath = src_dir / module_name.replace('.', os.sep)
    if not mpath.is_dir():
        mpath = mpath.with_suffix('.py')
        assert mpath.exists(), f"Expected module at {mpath}, but it doesn't exist"  # just in case
    return str(mpath)


_pytest.main.search_pypath = search_pypath  # type: ignore[assignment]
