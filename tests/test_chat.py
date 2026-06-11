import io
import locale
from wacb import wacbchat
from .wacbtesthelpers import *

def test_parseSystemMessage():
    wa = wacbchat.WaChat()
    addMessagesToChat(wa, [
        '[31.12.24, 20:52:25] Test: \u200eNachrichten und Anrufe sind Ende-zu-Ende-verschl\u00fcsselt. Nur Personen in diesem Chat k\u00f6nnen sie lesen, anh\u00f6ren oder teilen.\r\n'
    ])
    assert wa[0].isSystemMessage
    assert wa[0].time.year == 2024 and wa[0].time.month == 12 and wa[0].time.day == 31
    assert wa[0].time.hour == 20 and wa[0].time.minute == 52 and wa[0].time.second == 25

def test_parseMessage():
    wa = wacbchat.WaChat()
    addMessagesToChat(wa, [
        '[09.01.25, 15:48:14] Nobody: Drinnen oder drau\u00dfen?'
    ])
    assert wa[0].isUserMessage and wa[0].user == "Nobody"

def test_parseMessageFromUnknownUser():
    wa = wacbchat.WaChat()
    addMessagesToChat(wa, [
        '[12.01.25, 11:01:18] ~\u202fNobody: Look here.'
    ])
    assert wa[0].isUserMessage and wa[0].user.printable == "~Nobody"

def test_parseMessageWithAttachment():
    wa = ChatWithAttachments()
    wa.addAttachment("PHOTO-2025-01-17-09-48-45.jpg", "Dummy Data")
    addMessagesToChat(wa, [
        '\u200e[17.01.25, 09:48:45] Nobody: \u200e<Anhang: PHOTO-2025-01-17-09-48-45.jpg>'
    ])
    assert wa[0].isUserMessage and wa[0].user == "Nobody"
    assert wa[0].hasAttachment

def test_parseOldSystemMessage():
    wa = wacbchat.WaChat()
    addMessagesToChat(wa, [
        '20.10.16, 09:17:46: \u200eNachrichten in diesem Chat sowie Anrufe sind jetzt mit Ende-zu-Ende-Verschl\u00fcsselung gesch\u00fctzt.'
    ])
    assert wa[0].isSystemMessage
    assert wa[0].time.year == 2016 and wa[0].time.month == 10 and wa[0].time.day == 20
    assert wa[0].time.hour == 9 and wa[0].time.minute == 17 and wa[0].time.second == 46

def test_parseOldMessage():
    wa = wacbchat.WaChat()
    addMessagesToChat(wa, [
        '24.12.16, 13:08:16: Nobody: Frohe Weihnachten!'
    ])
    assert wa[0].isUserMessage and wa[0].user == "Nobody"

def test_parseOldMessageWithPhoneNumber():
    wa = wacbchat.WaChat()
    addMessagesToChat(wa, [
        '20.10.16, 11:29:55: \u202a+49\xa0123\xa045678901\u202c: Danke.'
    ])
    assert wa[0].isUserMessage and wa[0].user.printable == "+49 123 45678901"

def test_parseOldAttachment():
    wa = ChatWithAttachments()
    wa.addAttachment("PHOTO-0000001.jpg", "Dummy Data")
    addMessagesToChat(wa, [
        '25.10.16, 20:48:51: Nobody: PHOTO-0000001.jpg <\u200eangeh\u00e4ngt>'
    ])
    assert wa[0].isUserMessage and wa[0].user == "Nobody"
    assert wa[0].hasAttachment

def test_usLocaleMessage():
    wa = wacbchat.WaChat()
    addMessagesToChat(wa, [
        '[4/29/26, 3:18:14\u202fPM] Nobody: Hallo?'
    ])
    assert wa[0].isUserMessage and wa[0].user == "Nobody"
    assert wa[0].time.year == 2026 and wa[0].time.month == 4 and wa[0].time.day == 29
    assert wa[0].time.hour == 15 and wa[0].time.minute == 18 and wa[0].time.second == 14

def test_ukLocaleMessage():
    oldLocale = locale.getlocale(locale.LC_TIME)
    try:
        locale.setlocale(locale.LC_TIME, "uk")
        wa = wacbchat.WaChat()
        addMessagesToChat(wa, [
            '[07/05/2026, 3:18:14\u202fAM] Nobody: Hallo?'
        ])
    finally:
        locale.setlocale(locale.LC_TIME, "uk")
    assert wa[0].isUserMessage and wa[0].user == "Nobody"
    assert wa[0].time.year == 2026 and wa[0].time.month == 5 and wa[0].time.day == 7
    assert wa[0].time.hour == 3 and wa[0].time.minute == 18 and wa[0].time.second == 14

def test_exportAndImport():
    wa1 = makeTestChat()
    stream = io.BytesIO()
    wa1.exportToZip(stream)
    wa2 = wacbchat.ZippedChat(stream)
    assert len(wa1) == len(wa2)
    for i in range(len(wa1)):
        assert wa1[i] == wa2[i]

def test_merge():
    wa1 = makeTestChat()
    wa2 = wacbchat.WaChat()
    addMessagesToChat(wa2, [
        '[01.01.25, 15:48:14] Nobody: Drinnen oder drau\u00dfen?'
    ])
    wa = wacbchat.MergedChat([wa1, wa2, wa2])
    assert len(wa) == len(wa1) + len(wa2)
    for i in range(2, len(wa)):
        assert (wa[i].time - wa[i-1].time).total_seconds() >= 0
