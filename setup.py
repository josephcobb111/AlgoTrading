"""Setup file for the package, aliases;
.. code:: bash
    $ python setup.py lint
"""
import codecs
import os

import versioneer
from setuptools import setup, find_packages


def read(*parts):
    """
    Build an absolute path from *parts* and return the contents of the
    resulting file. Assume UTF-8 encoding.
    """
    with codecs.open(os.path.join(HERE, *parts), "rb", "utf-8") as f:
        return f.read()


def install_dependencies(links):
    """
    Install dependency links
    """
    for link in links:
        os.system("pip install" + link + " --upgrade")


# optionally read this from a requirements.txt file
# if this list is blank it reads from the requirements.txt file instead.
INSTALL_REQUIRES = []
DEPENDENCY_LINKS = []

HERE = os.path.abspath(os.path.dirname(__file__))
# read dependencies from requirements.txt
INSTALL_REQUIRES = [
    x
    for x in read("requirements.txt").split("\n")
    if x != ""
    and not x.startswith("#")
    and not x.startswith("-e")
    and not x.startswith("git+")
]

DEPENDENCY_LINKS = [
    x for x in read("requirements.txt").split("\n") if x.startswith("git+")
]

if __name__ == "__main__":
    install_dependencies(DEPENDENCY_LINKS)
    setup(
        name="algotrading",
        version=versioneer.get_version(),
        cmdclass=versioneer.get_cmdclass(),
        author="Joseph Cobb",
        author_email="joseph_cobb96@yahoo.com",
        url="https://github.com/josephcobb111/AlgoTrading",
        description="Package to support financial analyses.",
        include_package_data=True,
        dependency_links=DEPENDENCY_LINKS,
        install_requires=INSTALL_REQUIRES,
        packages=find_packages(),
    )
