from . import phorulib


def load_tests(loader, tests, ignore):
    phorulib.load_tests(loader, tests, ignore)
    return tests
