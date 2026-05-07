from wacb import wacbemoji
from .wacbtesthelpers import *

def test_numberSign():
    # Add an emoji for the number sign ("#").
    em = EmojiDatabaseForTest()
    em.addEmoji([35], getPngBlob())
    ej = wacbemoji.Emojify(em)
    # The emojifier should find the number sign for potential replacement.
    m = ej.find("test#it")
    assert m
    assert m.pos == 4
    assert m.end == 5
    assert m.emoji.isEmoji and m.emoji.isAscii
    # The number sign is an ASCII character. It should be ignored when the
    # "ignore ASCII" option is enabled.
    ej.ignoreAscii = True
    m = ej.find("test#it")
    assert not m

def test_numberSignWithKeycap():
    # The text contains "#" + emoji variation selector + combining enclosing keycap,
    # but we have an emoji for the "#" sign only. The emojifier should match the sign
    # that we have, and skip the following modifiers.
    em = EmojiDatabaseForTest()
    em.addEmoji([35], getPngBlob())
    ej = wacbemoji.Emojify(em)
    m = ej.find("test#\ufe0f\u20e3it")
    assert m
    assert m.pos == 4
    assert m.end == 7
    assert m.emoji.isEmoji and m.emoji.isAscii
    assert m.emoji.length == 1
    # When ignore ASCII is enabled, the plain number sign should not be found.
    ej.ignoreAscii = True
    m = ej.find("test#it")
    assert not m
    # Now we add an emoji for the entire sequence. Ignore ASCII is still on, but
    # this should not matter now, since we are now replacing a complex sequence
    # rather than just a single ASCII character.
    em.addEmoji([35, 65039, 8419], getPngBlob())
    m = ej.find("test#\ufe0f\u20e3it")
    assert m
    assert m.pos == 4
    assert m.end == 7
    assert m.emoji.isEmoji and not m.emoji.isAscii
    assert m.emoji.length == 3

def test_variationSelectorAtEnd():
    # Sometimes, the emoji variation selector appears at the end.
    # The file names in the noto-emoji emoji set do not include the
    # emoji variation selector at the end. Still, when emojifying,
    # we want to drop the variation selector at the end.
    em = EmojiDatabaseForTest()
    ej = wacbemoji.Emojify(em)
    em.addEmoji([129318, 8205, 9792], getPngBlob())
    assert "emoji_u1f926_200d_2640.png" in em
    assert ej.hasFile("/emoji/emoji_u1f926_200d_2640.png")
    m = ej.find("oops. \U0001f926\u200d\u2640\ufe0f")
    assert m
    assert m.pos == 6
    assert m.end == 10
    assert m.emoji.isEmoji and not m.emoji.isAscii
    assert m.emoji.path == [129318, 8205, 9792]
