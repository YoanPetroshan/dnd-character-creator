"""S06 (audit I18N-01): a Bulgarian plural card keeps its subordinate clause inside the plural filter, so the clause agrees
with the noun for one and for several ("оръжие, с което", "оръжия, с които"). The exact texts for n = 1, 2 and 5 are pinned."""
import pytest

from i18n.messages import MESSAGES, format_template

EXPECTED = {
    "desc-weapon-proficiency-choice": {
        1: "Изберете 1 оръжие, с което получавате владеене (Proficiency).",
        2: "Изберете 2 оръжия, с които получавате владеене (Proficiency).",
        5: "Изберете 5 оръжия, с които получавате владеене (Proficiency).",
    },
    "desc-feat-expertise": {
        1: "Изберете 1 умение (Skill), което владеете, за да получите експертиза (Expertise).",
        2: "Изберете 2 умения (Skills), които владеете, за да получите експертиза (Expertise).",
    },
    "desc-weapon-mastery-feat": {
        1: "Изберете 1 вид оръжие, с което владеете, за да използвате свойството му от Майсторство с оръжия (Weapon Mastery). "
           "Можете да смените избора след дълга почивка (Long Rest).",
        2: "Изберете 2 вида оръжие, с които владеете, за да използвате свойствата им от Майсторство с оръжия (Weapon Mastery). "
           "Можете да смените избора след дълга почивка (Long Rest).",
    },
    "desc-pick-fighting-style": {
        1: "Научете 1 опция Fighting Style от класа fighter. Тя трябва да се различава от всеки стил, който вече имате.",
        2: "Научете 2 опции Fighting Style от класа fighter. Те трябва да се различават от всеки стил, който вече имате.",
    },
}


@pytest.mark.parametrize("key,n", [(k, n) for k, by_n in EXPECTED.items() for n in by_n])
def test_the_subordinate_clause_agrees_with_the_noun(key, n):
    assert format_template(MESSAGES[key]["bg"], {"n": n}) == EXPECTED[key][n]
