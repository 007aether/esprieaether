"""Text server startup must not depend on optional speech packages."""
import subprocess
import sys


def test_server_imports_without_numpy():
    result = subprocess.run(
        [sys.executable, "-c", """
import builtins
original_import = builtins.__import__
def without_numpy(name, *args, **kwargs):
    if name == 'numpy' or name.startswith('numpy.'):
        raise ModuleNotFoundError('numpy is unavailable for text-only installation')
    return original_import(name, *args, **kwargs)
builtins.__import__ = without_numpy
import atulya.server
"""],
        # J159: l'import sans numpy prenait ~28 s seul ; 30 s tombait en timeout
        # quand une autre suite locale tournait en parallèle. L'assertion reste la même.
        capture_output=True, text=True, timeout=90,
    )
    assert result.returncode == 0, result.stderr
