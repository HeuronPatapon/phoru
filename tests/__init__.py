import unittest


from hpat.phoru.phorulib import Rule


import jq


def load_tests(loader, tests, ignore):
    import hpat.phoru
    tests.addTests(unittest.defaultTestLoader.loadTestsFromModule(hpat.phoru, pattern=ignore))
    return tests


class TestJQConversion(unittest.TestCase):
    def test_basic_substitutions(self):
        rule = Rule(source="aa", target="cde")
        text = rule.to_jq()
        self.assertEqual(text, (
            'gsub("(?<prefix>)(?<source>aa)(?<suffix>)"; "\\(.prefix)cde\\(.suffix)")'
        ))
        program = jq.compile(text)
        output = program.input("abaaf").first()
        self.assertEqual(output, "abcdef")

    def test_contextual_substitutions_no1(self):
        rule = Rule(source="a", target="e", suffix="c")
        text = rule.to_jq()
        self.assertEqual(text, (
            'gsub("(?<prefix>)(?<source>a)(?<suffix>c)"; "\\(.prefix)e\\(.suffix)")'
        ))
        program = jq.compile(text)
        output = program.input("abaac").first()
        self.assertEqual(output, "abaec")

    def test_contextual_substitutions_no2(self):
        rule = Rule(source="a", target="e", prefix="b")
        text = rule.to_jq()
        self.assertEqual(text, (
            'gsub("(?<prefix>b)(?<source>a)(?<suffix>)"; "\\(.prefix)e\\(.suffix)")'
        ))
        program = jq.compile(text)
        output = program.input("abaac").first()
        self.assertEqual(output, "abeac")

    def test_keeping_references_no1(self):
        rule = Rule(source=r"(a|e)", target="{_}r", suffix=r"(k|p)")
        text = rule.to_jq()
        self.assertEqual(text, (
            'gsub("(?<prefix>)(?<source>(a|e))(?<suffix>(k|p))"; "\\(.prefix)\\(.source)r\\(.suffix)")'
        ))
        program = jq.compile(text)
        output = program.input("kap").first()
        self.assertEqual(output, "karp")

    def test_keeping_references_no2(self):
        rule = Rule(source=r"(a|e)", target="{-prefix}{_}{+prefix}", prefix=r"(r|l)", suffix=r"(k|p)")
        text = rule.to_jq()
        self.assertEqual(text, (
            'gsub("(?<prefix>(r|l))(?<source>(a|e))(?<suffix>(k|p))"; "\\(.source)\\(.prefix)\\(.suffix)")'
        ))
        program = jq.compile(text)
        output = program.input("krap").first()
        self.assertEqual(output, "karp")

    def test_custom_references(self):
        rule = Rule(source=r"(a|e)", target="{+rhotic}{_}{-rhotic}", suffix=r"(?P<rhotic>(r|l))(?P<consonant>(k|p))")
        text = rule.to_jq()
        self.assertEqual(text, (
            'gsub("(?<prefix>)(?<source>(a|e))(?<rhotic>(r|l))(?<consonant>(k|p))"; "\\(.prefix)\\(.rhotic)\\(.source)\\(.consonant)")'
        ))
        program = jq.compile(text)
        output = program.input("karp").first()
        self.assertEqual(output, "krap")

    def test_other_source_manipulations_no1(self):
        rule = Rule(source=r"(a|e)", target="{+_}{+rhotic}{_}{-rhotic}", suffix=r"(?P<rhotic>(r|l))(?P<consonant>(k|p))")
        text = rule.to_jq()
        self.assertEqual(text, (
            'gsub("(?<prefix>)(?<source>(a|e))(?<rhotic>(r|l))(?<consonant>(k|p))"; "\\(.prefix)\\(.source)\\(.rhotic)\\(.source)\\(.consonant)")'
        ))
        program = jq.compile(text)
        output = program.input("karp").first()
        self.assertEqual(output, "karap")

    def test_other_source_manipulations_no2(self):
        rule = Rule(source=r"(a|e)", target="{+rhotic}{-_}o{-rhotic}", suffix=r"(?P<rhotic>(r|l))(?P<consonant>(k|p))")
        text = rule.to_jq()
        self.assertEqual(text, (
            'gsub("(?<prefix>)(?<source>(a|e))(?<rhotic>(r|l))(?<consonant>(k|p))"; "\\(.prefix)\\(.rhotic)o\\(.consonant)")'
        ))
        program = jq.compile(text)
        output = program.input("karp").first()
        self.assertEqual(output, "krop")

    def test_word_boundary(self):
        rule = Rule(source=r"(a|e)", target="{-_}o", prefix="#")
        text = rule.to_jq()
        self.assertEqual(text, (
            'gsub("(?<prefix>#)(?<source>(a|e))(?<suffix>)"; "\\(.prefix)o\\(.suffix)")'
        ))
        program = jq.compile(text)
        output = program.input("#arp#").first()
        self.assertEqual(output, "#orp#")

    def test_back_references_no1(self):
        rule = Rule(source=r"(?P<vowel>(a|e))(?P<consonant>(k|p))(?P=vowel)", target="o{+consonant}o{-_}")
        text = rule.to_jq()
        self.assertEqual(text, (
            'gsub("(?<prefix>)(?<vowel>(a|e))(?<consonant>(k|p))\\\\k<vowel>(?<suffix>)"; "\\(.prefix)o\\(.consonant)o\\(.suffix)")'
        ))
        program = jq.compile(text)
        expect_map = dict(
            akap="okop",
            ekep="okop",
            akep="akep",
        )
        for key, expected in expect_map.items():
            with self.subTest(key=key):
                output = program.input(key).first()
                self.assertEqual(output, expected)

    def test_back_references_no2(self):
        rule = Rule(source=r"(?P<vowel>(a|e))", target="{-_}o{+consonant}{-vowel}o{-consonant}", suffix=r"(?P<consonant>(k|p))(?P=vowel)")
        text = rule.to_jq()
        self.assertEqual(text, (
            'gsub("(?<prefix>)(?<vowel>(a|e))(?<consonant>(k|p))\\\\k<vowel>"; "\\(.prefix)o\\(.consonant)o")'
        ))
        program = jq.compile(text)
        expect_map = dict(
            akap="okop",
            ekep="okop",
            akep="akep",
        )
        for key, expected in expect_map.items():
            with self.subTest(key=key):
                output = program.input(key).first()
                self.assertEqual(output, expected)

    def test_mappings_no1(self):
        rule = Rule(source=r"(p|t|k)", target="{-_}{voiced[source]}", prefix=r"^", maps=dict(voiced=dict(p="b", t="d", k="g")))
        text = rule.to_jq()
        self.assertEqual(text, (
            '{"p": "b", "t": "d", "k": "g"} as $voiced | gsub("(?<prefix>^)(?<source>(p|t|k))(?<suffix>)"; "\\(.prefix)\\($voiced[.source])\\(.suffix)")'
        ))
        program = jq.compile(text)
        expect_map = dict(
            pat="bat",
            kat="gat",
        )
        for key, expected in expect_map.items():
            with self.subTest(key=key):
                output = program.input(key).first()
                self.assertEqual(output, expected)

    def test_mappings_no2(self):
        rule = Rule(source=r"(?P<sonorant>(r|l))", target="{-_}{dissimilate[sonorant]}", suffix=r"(?P<vowel>(a|e))(?P=sonorant)", maps=dict(dissimilate=dict(r="l", l="r")))
        text = rule.to_jq()
        self.assertEqual(text, (
            '{"r": "l", "l": "r"} as $dissimilate | gsub("(?<prefix>)(?<sonorant>(r|l))(?<vowel>(a|e))\\\\k<sonorant>"; "\\(.prefix)\\($dissimilate[.sonorant])\\(.vowel)\\(.sonorant)")'
        ))
        program = jq.compile(text)
        expect_map = dict(
            klali="krali",
            kreri="kleri",
        )
        for key, expected in expect_map.items():
            with self.subTest(key=key):
                output = program.input(key).first()
                self.assertEqual(output, expected)

    def test_mappings_no3(self):
        harmony = {
                ("a", "a"): "a",
                ("a", "e"): "a",
                ("a", "u"): "ɯ",
                ("e", "a"): "e",
                ("e", "e"): "e",
                ("e", "u"): "i",
                ("u", "a"): "a",
                ("u", "e"): "a",
                ("u", "u"): "u",
        }
        rule = Rule(source=r"(a|e|u)", target="{-_}{harmony[vowel,source]}", prefix=r"(?P<vowel>(a|e|u))(?P<consonant>(k|p))", maps=dict(harmony=harmony))
        text = rule.to_jq()
        self.assertEqual(text, (
            '{"a": {"a": "a", "e": "a", "u": "\\u026f"}, "e": {"a": "e", "e": "e", "u": "i"}, "u": {"a": "a", "e": "a", "u": "u"}} as $harmony | gsub("(?<vowel>(a|e|u))(?<consonant>(k|p))(?<source>(a|e|u))(?<suffix>)"; "\\(.vowel)\\(.consonant)\\($harmony[.vowel][.source])\\(.suffix)")'
        ))
        program = jq.compile(text)
        expect_map = dict(
            klepa="klepe",
            krepu="krepi",
            krapu="krapɯ",
        )
        for key, expected in expect_map.items():
            with self.subTest(key=key):
                output = program.input(key).first()
                self.assertEqual(output, expected)



if __name__ == '__main__':
    unittest.main()
