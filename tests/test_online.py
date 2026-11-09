from lunatranslator.engines.online import MyMemoryEngine

def test_german_result_rejected_for_english_target():
    assert MyMemoryEngine._looks_wrong_target_language("geht es dir gut?", "de", "en")

def test_english_result_not_rejected_for_english_target():
    assert not MyMemoryEngine._looks_wrong_target_language("Are you doing well?", "de", "en")

def test_unknown_language_is_not_guessed():
    assert not MyMemoryEngine._looks_wrong_target_language("some words", "xx", "yy")
