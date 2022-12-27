"""
Supply tools that are able to apply phonological rules to text inputs. 
"""
from typing import *
import sys
import re
import doctest
import string


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
    # -------------------
    >>> r = Rule(source="aa", target="cde")
    >>> r.pattern
    re.compile('(?P<prefix>)(?P<source>aa)(?P<suffix>)')
    >>> r.replacement
    '\\\\g<prefix>cde\\\\g<suffix>'
    >>> r
    <Rule aa := cde>
    >>> r("abaaf")
    'abcdef'

    # Contextual substitutions
    # ------------------------
    >>> r = Rule(source="a", target="e", suffix="c")
    >>> r.pattern
    re.compile('(?P<prefix>)(?P<source>a)(?P<suffix>c)')
    >>> r.replacement
    '\\\\g<prefix>e\\\\g<suffix>'
    >>> r
    <Rule a := e |  _ c>
    >>> r("abaac")
    'abaec'

    >>> r = Rule(source="a", target="e", prefix="b")
    >>> r.pattern
    re.compile('(?P<prefix>b)(?P<source>a)(?P<suffix>)')
    >>> r.replacement
    '\\\\g<prefix>e\\\\g<suffix>'
    >>> r
    <Rule a := e | b _ >
    >>> r("abaac")
    'abeac'

    # Keeping references
    # ------------------
    >>> r = Rule(source=r"(a|e)", target="{_}r", suffix=r"(k|p)")
    >>> r.pattern
    re.compile('(?P<prefix>)(?P<source>(a|e))(?P<suffix>(k|p))')
    >>> r.replacement
    '\\\\g<prefix>\\\\g<source>r\\\\g<suffix>'
    >>> r
    <Rule (a|e) := {_}r |  _ (k|p)>
    >>> r("kap")
    'karp'

    >>> r = Rule(source=r"(a|e)", target="{-prefix}{_}{+prefix}", prefix=r"(r|l)", suffix=r"(k|p)")
    >>> r.pattern
    re.compile('(?P<prefix>(r|l))(?P<source>(a|e))(?P<suffix>(k|p))')
    >>> r.replacement
    '\\\\g<source>\\\\g<prefix>\\\\g<suffix>'
    >>> r
    <Rule (a|e) := {-prefix}{_}{+prefix} | (r|l) _ (k|p)>
    >>> r("krap")
    'karp'

    # Custom references
    # -----------------
    >>> r = Rule(source=r"(a|e)", target="{+rhotic}{_}{-rhotic}", suffix=r"(?P<rhotic>(r|l))(?P<consonant>(k|p))")
    >>> r.pattern
    re.compile('(?P<prefix>)(?P<source>(a|e))(?P<rhotic>(r|l))(?P<consonant>(k|p))')
    >>> r.replacement
    '\\\\g<prefix>\\\\g<rhotic>\\\\g<source>\\\\g<consonant>'
    >>> r
    <Rule (a|e) := {+rhotic}{_}{-rhotic} |  _ (?P<rhotic>(r|l))(?P<consonant>(k|p))>
    >>> r("karp")
    'krap'

    # Other source manipulations
    # --------------------------
    >>> r = Rule(source=r"(a|e)", target="{+_}{+rhotic}{_}{-rhotic}", suffix=r"(?P<rhotic>(r|l))(?P<consonant>(k|p))")
    >>> r.pattern
    re.compile('(?P<prefix>)(?P<source>(a|e))(?P<rhotic>(r|l))(?P<consonant>(k|p))')
    >>> r.replacement
    '\\\\g<prefix>\\\\g<source>\\\\g<rhotic>\\\\g<source>\\\\g<consonant>'
    >>> r
    <Rule (a|e) := {+_}{+rhotic}{_}{-rhotic} |  _ (?P<rhotic>(r|l))(?P<consonant>(k|p))>
    >>> r("karp")
    'karap'

    >>> r = Rule(source=r"(a|e)", target="{+rhotic}{-_}o{-rhotic}", suffix=r"(?P<rhotic>(r|l))(?P<consonant>(k|p))")
    >>> r.pattern
    re.compile('(?P<prefix>)(?P<source>(a|e))(?P<rhotic>(r|l))(?P<consonant>(k|p))')
    >>> r.replacement
    '\\\\g<prefix>\\\\g<rhotic>o\\\\g<consonant>'
    >>> r
    <Rule (a|e) := {+rhotic}{-_}o{-rhotic} |  _ (?P<rhotic>(r|l))(?P<consonant>(k|p))>
    >>> r("karp")
    'krop'

    ~~~
    """
    class MiniLanguage(string.Formatter):
        KEY = r"(?P<sign>(\+|-))(?P<group>\w+)"

        def __init__(
                self,
                prefix_groups: Sequence[str],
                suffix_groups: Sequence[str]):
            # Note. prefix_groups and suffix_groups are presumed to not contain any duplicate values. 
            self.prefix_groups = prefix_groups
            self.suffix_groups = suffix_groups
            self.source_seen = False

        def format(self, *args, **kwargs):
            result = super().format(*args, **kwargs)
            # add the missing prefix groups and suffix groups
            prefix = ''.join([
                fr"\g<{prefix_group}>"
                for prefix_group in self.prefix_groups
            ])
            suffix = ''.join([
                fr"\g<{suffix_group}>"
                for suffix_group in self.suffix_groups
            ])

            return ''.join([prefix, result, suffix])

        def get_value(self, key, *args, **kwargs) -> str:
            if key == "_":
                group = "source"
                if not self.source_seen:
                    self.source_seen = True
                    return rf"\g<{group}>"
                else:
                    raise ValueError("source key cannot be duplicated")
            elif (match := re.match(self.KEY, key)) is not None:
                sign, group = match.group("sign", "group")
                if group == "_":
                    group = "source"

                if sign == "+":
                    return rf"\g<{group}>"
                elif group == "source":
                    if not self.source_seen:
                        self.source_seen = True
                        return str()
                    else:
                        raise ValueError("source key cannot be duplicated")
                else:
                    if not self.source_seen:
                        sequence = self.prefix_groups
                    else:
                        sequence = self.suffix_groups
                    index = sequence.index(group)
                    sequence.pop(index)
                    return str()

            else:
                raise ValueError(f"unexpected key: {key}")

    def __init__(
            self,
            source: Union[str, Ezre],
            *,
            target: str,
            suffix: Optional[Union[str, Ezre]]=None,
            prefix: Optional[Union[str, Ezre]]=None):
        # typing:
        if isinstance(source, str):
            source = Ezre(source)
        if suffix is None:
            suffix = Ezre("")
        elif isinstance(suffix, str):
            suffix = Ezre(suffix)
        if prefix is None:
            prefix = Ezre("")
        elif isinstance(prefix, str):
            prefix = Ezre(prefix)

        # for pretty printing:
        self.source: Ezre = source
        self.suffix: Ezre = suffix
        self.prefix: Ezre = prefix
        self.target: str = target

        # for actual processing:
        self.replacement: str = self.get_replacement()
        self.pattern: str = self.get_pattern()

    def get_replacement(self) -> str:
        # Note. regular expressions cannot contain multiple groups with the same name. 
        prefix_groups: List[str] = list(self.prefix.compiled.groupindex.keys())
        if not prefix_groups:
            prefix_groups = ["prefix"]

        suffix_groups: List[str] = list(self.suffix.compiled.groupindex.keys())
        if not suffix_groups:
            suffix_groups = ["suffix"]

        formatter = self.MiniLanguage(
            prefix_groups=prefix_groups,
            suffix_groups=suffix_groups)
        return formatter.format(self.target)

    def get_pattern(self) -> re.Pattern:
        # Note. this part avoid creating groups on top of existing ones
        # and assumes that 'pattern' results in a sequence of non-nested groups. 
        prefix_groups: List[str] = list(self.prefix.compiled.groupindex.keys())
        if not prefix_groups:
            prefix_pattern = self.prefix.group("prefix")
        else:
            prefix_pattern = self.prefix

        suffix_groups: List[str] = list(self.suffix.compiled.groupindex.keys())
        if not suffix_groups:
            suffix_pattern = self.suffix.group("suffix")
        else:
            suffix_pattern = self.suffix

        # TODO: support for source groups?
        source_pattern = self.source.group("source")

        pattern: Ezre = prefix_pattern + source_pattern + suffix_pattern
        return pattern.compiled

    def __repr__(self):
        # TODO: support for a nicer replacement display (removing the brackets)
        # TODO: maybe also a nicer display for the prefix/suffix groups
        if len(str(self.prefix)) == 0 and len(str(self.suffix)) == 0:
            return f"<{type(self).__name__} {self.source} := {self.target}>"
        else:
            return f"<{type(self).__name__} {self.source} := {self.target} | {self.prefix} _ {self.suffix}>"

    def __call__(self, string: str, **kwargs):
        return re.sub(self.pattern, self.replacement, string, **kwargs)

    def to_jq(self) -> str:
        """
        Convert this rule as a JQ program. 

        Description
        -----------
        - convert '(?P<name>...)' into '(?<name>...)'
        - convert '(?P=name)' into '\\k<name>'
        - convert '\\g<name>' into '\\k<name>'

        References
        ----------
        - https://stedolan.github.io/jq/manual/#RegularexpressionsPCRE
        - https://www.pcre.org/original/doc/html/pcresyntax.html
        """
        return _to_jq(self)


class _to_jq:
    # Note. use of non-greedy capture for 'GROUP', to cope with parentheses:
    GROUP = re.compile(r"\(\?P<(?P<name>\w+)>(?P<pattern>.*?)\)")
    BACKREF = re.compile(r"\(\?P=(?P<name>\w+)\)")
    REPLREF = re.compile(r"\\g<(?P<name>\w+)>")

    def __new__(cls, rule: Rule) -> str:
        regex: str = rule.pattern.pattern
        replacement: str = rule.replacement
        # TODO: proper escaping
        if '"' in regex:
            raise NotImplementedError(f"cannot escape {regex=!r}")
        if '"' in replacement:
            raise NotImplementedError(f"cannot escape {replacement=!r}")

        regex = cls.GROUP.sub(r"(?<\g<name>>\g<pattern>)", regex)
        regex = cls.BACKREF.sub(r"\\k<\g<name>>", regex)
        replacement = cls.REPLREF.sub(r"\(.\g<name>)", replacement)
        return f'gsub("{regex!s}"; "{replacement!s}")'
