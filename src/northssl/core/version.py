from importlib.metadata import PackageNotFoundError, version as package_version

from northssl import __version__

def get_northssl_version() -> str:
    try:
        return package_version("northssl")
    except PackageNotFoundError:
        return __version__
