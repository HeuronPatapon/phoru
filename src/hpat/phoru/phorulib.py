"""
Supply tools that are able to apply phonological rules to text inputs. 
"""
from typing import *
import re
import doctest


from hpat.ezre import Ezre


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(__name__))
    return tests


class Rule:
    """
    Examples
    --------
    ~~~python

    # Basic substitutions
    >>> r = Rule(source=Ezre("a"), becomes="b")
    >>> r
    <Rule a := b>
    >>> r("abaac")
    'bbbbc'

    >>> r = Rule(source=Ezre("aa"), becomes="b")
    >>> r
    <Rule aa := b>
    >>> r("abaac")
    'abbc'

    >>> r = Rule(source=Ezre("a"), becomes="bb")
    >>> r
    <Rule a := bb>
    >>> r("abaac")
    'bbbbbbbc'

    # Contextual substitutions
    >>> r = Rule(source=Ezre("a"), becomes="b", before=Ezre("c"))
    >>> r
    <Rule a := b |  _ c>
    >>> r("abaac")
    'ababc'

    >>> r = Rule(source=Ezre("a"), becomes="b", after=Ezre("b"))
    >>> r
    <Rule a := b | b _ >
    >>> r("abaac")
    'abbac'

    # Using sets
    >>> r = Rule(source=Ezre.from_sequence({"a", "e"}), becomes="b")
    >>> r
    <Rule (a|e) := b>
    >>> r("abaec")
    'bbbbc'

    >>> r = Rule(source=Ezre.from_sequence({"a", "e"}), becomes="b", before=Ezre("c"))
    >>> r
    <Rule (a|e) := b |  _ c>
    >>> r("abaec")
    'ababc'

    >>> r = Rule(source=Ezre.from_sequence({"a", "e"}), becomes="{__source__}b", before=Ezre("c"))
    >>> r
    <Rule (a|e) :=  _ b |  _ c>
    >>> r("abaecac")
    'abaebcabc'

    ~~~
    """

    __pre__ = r"\g<pre>"
    __source__ = r"\g<src>"
    __post__ = r"\g<post>"

    def __init__(
            self,
            *,
            source: Ezre,
            becomes: str,
            before: Optional[Ezre]=None,
            after: Optional[Ezre]=None):
        if before is None:
            before = Ezre("")
        if after is None:
            after = Ezre("")
        # Kept for pretty-printing:
        self.source = source
        self.becomes = becomes.format(__source__=" _ ")
        self.before = before
        self.after = after
        # The important attributes:
        self.pattern: str = (
            self.after.group("pre")
            + self.source.group("src")
            + self.before.group("post")
        ).re
        self.replacement: str = (
            self.__pre__
            + becomes.format(__source__=self.__source__)
            + self.__post__
        )

    def __repr__(self):
        if len(str(self.after)) == 0 and len(str(self.before)) == 0:
            return f"<{type(self).__name__} {self.source} := {self.becomes}>"
        else:
            return f"<{type(self).__name__} {self.source} := {self.becomes} | {self.after} _ {self.before}>"

    def __call__(self, string: str, **kwargs):
        return re.sub(self.pattern, self.replacement, string, **kwargs)
