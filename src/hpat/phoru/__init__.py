from . import phorulib
from .phorulib import Rule


def load_tests(loader, tests, ignore):
    phorulib.load_tests(loader, tests, ignore)
    return tests
