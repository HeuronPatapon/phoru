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


if __name__ == '__main__':
    unittest.main()
