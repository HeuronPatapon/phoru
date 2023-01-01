"""
Supply tools that are able to apply phonological rules to text inputs. 
"""
from typing import *
import sys
import re
import doctest
import string
import functools
from collections import defaultdict
import json


from hpat.ezre import Ezre


__all__ = ("Rule",)


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(__name__))
    return tests


GroupName = NewType("GroupName", str)
MappingName = NewType("MappingName", str)
UserMapping = NewType("UserMapping", Dict[Union[GroupName, Tuple[GroupName]], str])


class Rule:
    """
    A phonological rule. 

    Description
    -----------
    Phonological rules allows to describe how sounds are transformed given a certain environment. 

    This class has been designed primarily with the use cas of phonological rules in mind, but can be used for other kinds of string manipulations, typically involving regular expressions. 

    Rules are callable instances:  after its creation, a `Rule` instance can be applied onto a string, returning the string after transformation. 


    Parameters
    ----------
    source
        The original element that will be subject to change in the appropriate context. 

    prefix, suffix
        Parameters `prefix` and `suffix` help to define the context for the change.  The prefix is the part right before the source, and the suffix is the part right after the source. 

        These parameters are optional, and it is equivalently possible to define the context within the `source` parameter. 

        See Examples below for more information. 

    target
        Description of how the source and its context is affected by the change. 

        See `Rule.MiniLanguage` for more information about its syntax. 


    Other Parameters
    ----------------
    count, flags
        Same as `re.sub`.  These parameters are applied each time the rule is called to make a transformation. 

    maps
        Placeholder for declaring custom mappings with user-supplied names, related to the `target` parameter. 

        Mappings represent deterministic transformations of a sound into another, potentially based on other sounds in the current context. 

        See Examples below for more information. 


    Attributes
    ----------
    pattern
        A regular expression pattern, originating from the `source`, `prefix` and `suffix` parameters. 

    replacement
        A substitution, related to the `pattern` attribute. 


    See Also
    --------
    `re.sub`


    Examples
    --------
    Basic substitutions
    ~~~~~~~~~~~~~~~~~~~
    Change "aa" into "cde":

        >>> r = Rule(source="aa", target="cde")
        >>> r.pattern
        re.compile('(?P<prefix>)(?P<source>aa)(?P<suffix>)')
        >>> r.replacement
        '\\\\g<prefix>cde\\\\g<suffix>'
        >>> repr(r)
        '<Rule aa := cde>'
        >>> r("abaaf")
        'abcdef'

    Contextual substitutions
    ~~~~~~~~~~~~~~~~~~~~~~~~
    Change "a" into "e" when followed by "c":

        >>> r = Rule(source="a", target="e", suffix="c")
        >>> r.pattern
        re.compile('(?P<prefix>)(?P<source>a)(?P<suffix>c)')
        >>> r.replacement
        '\\\\g<prefix>e\\\\g<suffix>'
        >>> repr(r)
        '<Rule a := e |  _ c>'
        >>> r("abaac")
        'abaec'

    Change "a" into "e" when following "b":

        >>> r = Rule(source="a", target="e", prefix="b")
        >>> r.pattern
        re.compile('(?P<prefix>b)(?P<source>a)(?P<suffix>)')
        >>> r.replacement
        '\\\\g<prefix>e\\\\g<suffix>'
        >>> repr(r)
        '<Rule a := e | b _ >'
        >>> r("abaac")
        'abeac'

    Keeping references
    ~~~~~~~~~~~~~~~~~~
    Add rhotic "r" after vowels "a" and "e" when followed by consonants "k" or "p":

        >>> r = Rule(source=r"(a|e)", target="{_}r", suffix=r"(k|p)")
        >>> r.pattern
        re.compile('(?P<prefix>)(?P<source>(a|e))(?P<suffix>(k|p))')
        >>> r.replacement
        '\\\\g<prefix>\\\\g<source>r\\\\g<suffix>'
        >>> repr(r)
        '<Rule (a|e) := {_}r |  _ (k|p)>'
        >>> r("kap")
        'karp'

    Metathesis:  move sonorant "r" and "l" around, from **before to after** vowels "a" and "e", when followed by consonants "k" or "p":

        >>> r = Rule(source=r"(a|e)", target="{-prefix}{_}{+prefix}", prefix=r"(r|l)", suffix=r"(k|p)")
        >>> r.pattern
        re.compile('(?P<prefix>(r|l))(?P<source>(a|e))(?P<suffix>(k|p))')
        >>> r.replacement
        '\\\\g<source>\\\\g<prefix>\\\\g<suffix>'
        >>> repr(r)
        '<Rule (a|e) := {-prefix}{_}{+prefix} | (r|l) _ (k|p)>'
        >>> r("krap")
        'karp'

    Custom references
    ~~~~~~~~~~~~~~~~~
    Metathesis:  move sonorant "r" and "l" around, from **after to before** vowels "a" and "e", when followed by consonants "k" or "p":

        >>> r = Rule(source=r"(a|e)", target="{+rhotic}{_}{-rhotic}", suffix=r"(?P<rhotic>(r|l))(?P<consonant>(k|p))")
        >>> r.pattern
        re.compile('(?P<prefix>)(?P<source>(a|e))(?P<rhotic>(r|l))(?P<consonant>(k|p))')
        >>> r.replacement
        '\\\\g<prefix>\\\\g<rhotic>\\\\g<source>\\\\g<consonant>'
        >>> repr(r)
        '<Rule (a|e) := {+rhotic}{_}{-rhotic} |  _ (?P<rhotic>(r|l))(?P<consonant>(k|p))>'
        >>> r("karp")
        'krap'

    Other source manipulations
    ~~~~~~~~~~~~~~~~~~~~~~~~~~
    Echo the vowel "a" and "e" before the sonorant "r" and "l" when followed by consonants "k" or "p":

        >>> r = Rule(source=r"(a|e)", target="{+_}{+rhotic}{_}{-rhotic}", suffix=r"(?P<rhotic>(r|l))(?P<consonant>(k|p))")
        >>> r.pattern
        re.compile('(?P<prefix>)(?P<source>(a|e))(?P<rhotic>(r|l))(?P<consonant>(k|p))')
        >>> r.replacement
        '\\\\g<prefix>\\\\g<source>\\\\g<rhotic>\\\\g<source>\\\\g<consonant>'
        >>> repr(r)
        '<Rule (a|e) := {+_}{+rhotic}{_}{-rhotic} |  _ (?P<rhotic>(r|l))(?P<consonant>(k|p))>'
        >>> r("karp")
        'karap'

    Combine neutralization of vowels "a" and "e" into a single sound "o" while moving the rhotic from after to before the vowel, when followed by consonant "k" or "p":

        >>> r = Rule(source=r"(a|e)", target="{+rhotic}{-_}o{-rhotic}", suffix=r"(?P<rhotic>(r|l))(?P<consonant>(k|p))")
        >>> r.pattern
        re.compile('(?P<prefix>)(?P<source>(a|e))(?P<rhotic>(r|l))(?P<consonant>(k|p))')
        >>> r.replacement
        '\\\\g<prefix>\\\\g<rhotic>o\\\\g<consonant>'
        >>> repr(r)
        '<Rule (a|e) := {+rhotic}{-_}o{-rhotic} |  _ (?P<rhotic>(r|l))(?P<consonant>(k|p))>'
        >>> r("karp")
        'krop'

    Word boundary
    ~~~~~~~~~~~~~
    Use the character '#' to represent a word boundary, instead of regular expression characters '^' and '$':

        >>> r = Rule(source=r"(a|e)", target="{-_}o", prefix=r"#")
        >>> r.pattern
        re.compile('(?P<prefix>#)(?P<source>(a|e))(?P<suffix>)')
        >>> r.replacement
        '\\\\g<prefix>o\\\\g<suffix>'
        >>> repr(r)
        '<Rule (a|e) := {-_}o | # _ >'
        >>> r("#arp#")
        '#orp#'

    Back references
    ~~~~~~~~~~~~~~~
    Neutralise a sequence of twice the **same vowel**, either "a" or "e", to "o", separated by a consonant "k" or "p":

        >>> r = Rule(source=r"(?P<vowel>(a|e))(?P<consonant>(k|p))(?P=vowel)", target="o{+consonant}o{-_}")
        >>> r.pattern
        re.compile('(?P<prefix>)(?P<vowel>(a|e))(?P<consonant>(k|p))(?P=vowel)(?P<suffix>)')
        >>> r.replacement
        '\\\\g<prefix>o\\\\g<consonant>o\\\\g<suffix>'
        >>> repr(r)
        '<Rule (?P<vowel>(a|e))(?P<consonant>(k|p))(?P=vowel) := o{+consonant}o{-_}>'
        >>> r("akap"), r("ekep"), r("akep")
        ('okop', 'okop', 'akep')

    Same transformation, different model:

        >>> r = Rule(source=r"(?P<vowel>(a|e))", target="{-_}o{+consonant}{-vowel}o{-consonant}", suffix=r"(?P<consonant>(k|p))(?P=vowel)")
        >>> r.pattern
        re.compile('(?P<prefix>)(?P<vowel>(a|e))(?P<consonant>(k|p))(?P=vowel)')
        >>> r.replacement
        '\\\\g<prefix>o\\\\g<consonant>o'
        >>> repr(r)
        '<Rule (?P<vowel>(a|e)) := {-_}o{+consonant}{-vowel}o{-consonant} |  _ (?P<consonant>(k|p))(?P=vowel)>'
        >>> r("akap"), r("ekep"), r("akep")
        ('okop', 'okop', 'akep')

    Mappings
    ~~~~~~~~
    Transform a voiceless consonant at the beginning of a word into a voiced version:

        >>> r = Rule(source=r"(p|t|k)", target="{-_}{voiced[source]}", prefix=r"^", maps=dict(voiced=dict(p="b", t="d", k="g")))
        >>> r.pattern
        re.compile('(?P<prefix>^)(?P<source>(p|t|k))(?P<suffix>)')
        >>> r.replacement
        '\\\\g<prefix>{voiced[source]}\\\\g<suffix>'
        >>> r.map_calls
        {('voiced', 'source')}
        >>> repr(r)
        "<Rule (p|t|k) := {-_}{voiced[source]} | ^ _  & voiced={'p': 'b', 't': 'd', 'k': 'g'}>"
        >>> r("pat"), r("kat")
        ('bat', 'gat')

    Dissimilate a sonorant: 

        >>> r= Rule(source=r"(?P<sonorant>(r|l))", target="{-_}{dissimilate[sonorant]}", suffix=r"(?P<vowel>(a|e))(?P=sonorant)", maps=dict(dissimilate=dict(r="l", l="r")))
        >>> r.pattern
        re.compile('(?P<prefix>)(?P<sonorant>(r|l))(?P<vowel>(a|e))(?P=sonorant)')
        >>> r.replacement
        '\\\\g<prefix>{dissimilate[sonorant]}\\\\g<vowel>\\\\g<sonorant>'
        >>> r.map_calls
        {('dissimilate', 'sonorant')}
        >>> repr(r)
        "<Rule (?P<sonorant>(r|l)) := {-_}{dissimilate[sonorant]} |  _ (?P<vowel>(a|e))(?P=sonorant) & dissimilate={'r': 'l', 'l': 'r'}>"
        >>> r("klali"), r("kreri")
        ('krali', 'kleri')

    Vowel harmony:  All vowels will take on the [+/- back] value of the vowel that precedes it, regardless of the number of intervening consonants. If a vowel is [+ high], it will also take on the [+/- round] value of the preceding vowel, regardless of the number of intervening consonants. 

        >>> harmony = {
        ... ("a", "a"): "a",
        ... ("a", "e"): "a",
        ... ("a", "u"): "ɯ",
        ... ("e", "a"): "e",
        ... ("e", "e"): "e",
        ... ("e", "u"): "i",
        ... ("u", "a"): "a",
        ... ("u", "e"): "a",
        ... ("u", "u"): "u",
        ... }
        >>> r= Rule(source=r"(a|e|u)", target="{-_}{harmony[vowel,source]}", prefix=r"(?P<vowel>(a|e|u))(?P<consonant>(k|p))", maps=dict(harmony=harmony))
        >>> r.pattern
        re.compile('(?P<vowel>(a|e|u))(?P<consonant>(k|p))(?P<source>(a|e|u))(?P<suffix>)')
        >>> r.replacement
        '\\\\g<vowel>\\\\g<consonant>{harmony[vowel,source]}\\\\g<suffix>'
        >>> r.map_calls
        {('harmony', 'vowel', 'source')}
        >>> repr(r)
        "<Rule (a|e|u) := {-_}{harmony[vowel,source]} | (?P<vowel>(a|e|u))(?P<consonant>(k|p)) _  & harmony={('a', 'a'): 'a', ('a', 'e'): 'a', ('a', 'u'): 'ɯ', ('e', 'a'): 'e', ('e', 'e'): 'e', ('e', 'u'): 'i', ('u', 'a'): 'a', ('u', 'e'): 'a', ('u', 'u'): 'u'}>"
        >>> r("klepa"), r("krepu"), r("krapu")
        ('klepe', 'krepi', 'krapɯ')
    """
    class MiniLanguage(string.Formatter):
        """
        Convert the `target` parameter of the Rule class into a `re.sub`-compliant string. 


        Syntax
        ------
        The syntax is the same as the Python format-string syntax, using '{' and '}' as special characters to delimit interpolations. 

        The syntax is as follows:

        [STR] [[GROUP_REF [STR]] ...] SOURCE_REF [STR] [[GROUP_REF [STR]] ...]

        Where:

        SOURCE_REF
            | '{_}'
            |'{-_}'
            | MAP_CALL

        GROUP_REF
            | '{+' GROUP_NAME '}'
            | '{-' GROUP_NAME '}'
            | MAP_CALL

        MAP_CALL
            | '{' MAP_NAME '[' GROUP_NAME [[',' GROUP_NAME] ...] ']' '}'

        STR
            Any sequence of characters. 

        MAP_NAME
            Name of a user-supplied mapping, same name as in rule's maps. 

            The MAP_NAME is followed by the names of the groups to be used as arguments of the mapping call. 

        GROUP_NAME
            Name of a group, same as in rule's source, prefix or suffix. 

            Users can define their own groups. 

        '{_}'
            Indicates the position of the rule's source. 

            Cannot be repeated. 

        '{-' GROUP_NAME '}'
            Indicates that the group must be removed. 

            Cannot be repeated. 

        '{+' GROUP_NAME '}'
            Indicates where the group must be added. 

            Can be repeated. 


        Shortcuts
        ---------
        - '{+_}' is equivalent to '{+source}'
        - '{-_}' is equivalent to '{-source}'


        Caution
        -------
        If a literal '{' character is needed, it must be escaped, which is done by doubling it (refer to Python format string syntax for this). 


        See Also
        --------
        https://docs.python.org/3.9/library/string.html#format-string-syntax
        """
        GROUP_REF = re.compile(
            r"(?P<sign>(\+|-)?)(?P<group>\w+)"
        )
        MAP_CALL = re.compile(
            r"(?P<map_name>\w+)\[(?P<groups>\w+(,\w+)*)\]"
        )

        def __init__(
                self,
                prefix_groups: Sequence[str],
                suffix_groups: Sequence[str],
                maps: Dict[MappingName, UserMapping]):
            # Note. prefix_groups and suffix_groups are presumed to not contain any duplicate values. 
            # CAUTION. prefix_groups and suffix_groups will be modified, so we make a copy:
            self.prefix_groups = list(prefix_groups)
            self.suffix_groups = list(suffix_groups)
            self.source_seen = False
            self.maps = maps
            self.map_calls: Set[Tuple[str]] = set()

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

        def get_value(self, key, args, kwargs) -> str:
            if key == "_":
                group = "source"
                if not self.source_seen:
                    self.source_seen = True
                    return rf"\g<{group}>"
                else:
                    raise ValueError("duplicated source cannot be written with '{_}', use '{+_}' instead. ")
            elif (match := self.GROUP_REF.match(key)) is not None:
                sign, group = match.group("sign", "group")
                if group == "_":
                    group = "source"

                # Note. None corresponds to the 'mapping' support:
                if sign is None:
                    return group
                elif sign == "+":
                    return rf"\g<{group}>"
                elif group == "source":
                    if not self.source_seen:
                        self.source_seen = True
                        return str()
                    else:
                        raise ValueError("key '{-_}' cannot be duplicated. ")
                else:
                    if not self.source_seen:
                        sequence = self.prefix_groups
                    else:
                        sequence = self.suffix_groups
                    index = sequence.index(group)
                    # CAUTION. modify prefix_groups, suffix_groups:
                    sequence.pop(index)
                    return str()

            else:
                raise ValueError(f"unsupported key format: {key!r}. ")

        def get_field(self, field_name, args, kwargs) -> str:
            if (match := self.MAP_CALL.match(field_name)) is not None:
                map_name = match.group("map_name")
                groups = match.group("groups").split(",")
                if map_name in self.maps:
                    map_call = (map_name, *groups)
                    self.map_calls.add(map_call)
                    return f"{{{field_name}}}", map_name
                else:
                    raise ValueError(f"mapping {map_name=} is used but not declared. ")
            else:
                return super().get_field(field_name, args, kwargs)


    def __init__(
            self,
            source: Union[str, Ezre],
            *,
            target: str,
            suffix: Optional[Union[str, Ezre]]=None,
            prefix: Optional[Union[str, Ezre]]=None,
            count: int=0,
            flags: int=0,
            maps: Optional[Dict[MappingName, UserMapping]]=None,
        ):
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

        self.maps = maps or dict()
        self.map_calls: Set[Tuple[str]] = set()

        # for pretty printing:
        self.source: Ezre = source
        self.suffix: Ezre = suffix
        self.prefix: Ezre = prefix
        self.target: str = target

        # for actual processing:
        self.replacement: str = self.get_replacement()
        self.pattern: str = self.get_pattern()
        self.count = count
        self.flags = flags

    def get_replacement(self) -> str:
        # Note. regular expressions cannot contain multiple groups with the same name. 
        prefix_groups: List[str] = self.get_groups(self.prefix)
        if not prefix_groups:
            prefix_groups = ["prefix"]

        suffix_groups: List[str] = self.get_groups(self.suffix)
        if not suffix_groups:
            suffix_groups = ["suffix"]

        formatter = self.MiniLanguage(
            prefix_groups=prefix_groups,
            suffix_groups=suffix_groups,
            maps=self.maps,
        )
        replacement = formatter.format(self.target)
        self.map_calls.update(formatter.map_calls)
        return replacement

    def replacer(self, match: re.Match) -> str:
        data = defaultdict(dict)
        for map_call in self.map_calls:
            map_name, *groups = map_call
            values = match.group(*groups)
            data[map_name][','.join(groups)] = self.maps[map_name][values]
        return match.expand(self.replacement).format(**data)

    @functools.cache
    def get_groups(self, pattern: Ezre) -> List[str]:
        """
        Get the list of groups, defined or referenced, in the given pattern. 

        See Also
        --------
        re.Pattern.groupindex
        """
        # CAUTION. internally, Rules relie on the definition of a prefix and a suffix, in order to make them more readable. 
        # This comes at the cost that only the `pattern` attribute can be safely assumed to end up being a suitable regular expression pattern, while `prefix` and `suffix` can be incomplete. 
        # It is typically the case when the user defines a group in the prefix and references it into the suffix. 
        # The user may reuse a group defined in prefix/source into the source/suffix, and in those cases, `groupindex` raises an error because the referree is undefined in source/suffix. 

        groups = dict()

        for match in _to_jq.BACKREF.finditer(pattern.re):
            groups[match.start("name")] = match.group("name")

        for match in _to_jq.GROUP.finditer(pattern.re):
            groups[match.start("name")] = match.group("name")

        return [groups[key] for key in sorted(groups)]

    def get_pattern(self) -> re.Pattern:
        """
        Create the appropriate pattern out of the source, prefix and suffix parameters. 

        If there is no user-defined group for either, default groups are supplied instead, namely 'source', 'prefix' and 'suffix'. 

        Caution
        -------
        assumes that 'pattern' results in a sequence of non-nested groups. 
        """
        prefix_groups: List[str] = self.get_groups(self.prefix)
        if not prefix_groups:
            prefix_pattern = self.prefix.group("prefix")
        else:
            prefix_pattern = self.prefix

        suffix_groups: List[str] = self.get_groups(self.suffix)
        if not suffix_groups:
            suffix_pattern = self.suffix.group("suffix")
        else:
            suffix_pattern = self.suffix

        # Note. support for source groups (expected to be declared and managed by the user):
        source_groups: List[str] = self.get_groups(self.source)
        if not source_groups:
            source_pattern = self.source.group("source")
        else:
            source_pattern = self.source

        pattern: Ezre = prefix_pattern + source_pattern + suffix_pattern
        return pattern.compiled

    def __repr__(self):
        if self.map_calls:
            maps = list()
            for map_call in self.map_calls:
                map_name, *_ = map_call
                map_ = self.maps[map_name]
                maps.append(f"{map_name}={map_}")
            maps = " & " + ", ".join(maps)
        else:
            maps = str()

        if len(str(self.prefix)) == 0 and len(str(self.suffix)) == 0:
            return f"<{type(self).__name__} {self.source} := {self.target}{maps}>"
        else:
            return f"<{type(self).__name__} {self.source} := {self.target} | {self.prefix} _ {self.suffix}{maps}>"

    def __call__(self, string: str):
        if not self.map_calls:
            replacer = self.replacement
        else:
            replacer = self.replacer
        return re.sub(
            self.pattern,
            replacer,
            string,
            count=self.count,
            flags=self.flags)

    def to_jq(self) -> str:
        """
        Convert this rule as a JQ program. 

        Description
        -----------
        - convert '(?P<name>...)' into '(?<name>...)'
        - convert '(?P=name)' into '\\k<name>'
        - convert '\\g<name>' into '\\k<name>'
        - support for custom mappings

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
    MAP_CALL = re.compile(
        r"{"
        # Note.  this part is the same as Rule.MiniLanguage.MAP_CALL:
        r"(?P<map_name>\w+)\[(?P<groups>\w+(,\w+)*)\]"
        "}"
    )

    @classmethod
    def replace_map_call(cls, match) -> str:
        map_name, groups = match.group("map_name", "groups")
        groups = groups.split(",")
        groups = "".join([f"[.{group}]" for group in groups])
        # Note. use an extra variable in jq for holding the mapping elsewhere:
        return match.expand(fr"\($\g<map_name>{groups})").format(groups=groups)

    @classmethod
    def normalize_mapping(cls, mapping: UserMapping):
        """
        Convert user-supplied mapping into a structure compatible with JSON. 
        """
        result = dict()
        for key, value in mapping.items():
            *subkeys, last_key = key
            subdict = result
            for subkey in subkeys:
                subdict = subdict.setdefault(subkey, dict())
            subdict[last_key] = value

        return result

    def __new__(cls, rule: Rule) -> str:
        regex: str = rule.pattern.pattern
        replacement: str = rule.replacement
        count: int = rule.count
        flags: int = rule.flags
        # TODO: proper escaping
        # TODO: support for count and flags
        if '"' in regex:
            raise NotImplementedError(f"cannot escape {regex=!r}")
        if '"' in replacement:
            raise NotImplementedError(f"cannot escape {replacement=!r}")
        if flags != 0:
            raise NotImplementedError("does not support Python re.flags")
        if count != 0:
            raise NotImplementedError("does not support count. ")

        regex = cls.GROUP.sub(r"(?<\g<name>>\g<pattern>)", regex)
        regex = cls.BACKREF.sub(r"\\\\k<\g<name>>", regex)
        replacement = cls.REPLREF.sub(r"\(.\g<name>)", replacement)
        replacement = cls.MAP_CALL.sub(cls.replace_map_call, replacement)

        if not rule.map_calls:
            return f'gsub("{regex!s}"; "{replacement!s}")'
        else:
            map_decl = list()
            for map_call in rule.map_calls:
                map_name, *_ = map_call
                mapping = json.dumps(cls.normalize_mapping(rule.maps[map_name]))
                map_decl.append(f"{mapping!s} as ${map_name!s}")
            map_decl = " | ".join(map_decl)
            return f'{map_decl!s} | gsub("{regex!s}"; "{replacement!s}")'
