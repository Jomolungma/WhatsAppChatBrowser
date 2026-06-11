import io
import base64
from wacb import wacbchat
from wacb import wacbemoji
from wacb import wacbconfig
from wacb import wacbhtml
from wacb import wacbapp

class ChatWithAttachments(wacbchat.WaChat):
    def __init__(self):
        super().__init__()
        self.attachments = {}

    def addAttachment(self, fileName, data):
        self.attachments[fileName] = data

    def hasFile(self, name):
        return name in self.attachments

    def openFile(self, name):
        return io.BytesIO(self.attachments[name])

    def copyFile(self, name, outputFile, updatecb=None):
        outputFile.write(self.attachments[name])

    def getFileSize(self, name):
        return len(self.attachments[name])

def addMessagesToChat(chat, lines):
    oldLength = len(chat)
    for line in lines:
        chat.parseAndAddMessage(line)
    assert len(chat) == oldLength + len(lines)

class EmojiDatabaseForTest(wacbemoji.Database):
    def __init__(self):
        super().__init__()

    def getType(self):
        return "image/png"

    def getName(self, path, emojiData):
        return self.codePointsToName(path)

    def getImage(self, path, emojiData):
        return emojiData

    def getBase64(self, path, emojiData):
        return base64.b64encode(emojiData).decode()

def getPngBlob():
    return base64.b64decode(b'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAEAQMAAACJA+yzAAAABlBMVEUAAAD///+l2Z/dAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAEElEQVQImWP4z/Cf4Q/DDwAP6APzJgLPPwAAAABJRU5ErkJggg==')

def makeTestChat():
    wa = ChatWithAttachments()
    wa.addAttachment("blob.png", getPngBlob())
    addMessagesToChat(wa, [
        '[31.12.24, 20:52:25] Test: \u200eNachrichten und Anrufe sind Ende-zu-Ende-verschl\u00fcsselt. Nur Personen in diesem Chat k\u00f6nnen sie lesen, anh\u00f6ren oder teilen.\r\n',
        '[31.12.24, 23:59:59] Somebody: Happy new year! \u2764',
        '[09.01.25, 15:48:14] Nobody: *Drinnen* oder _drau\u00dfen_?',
        '[12.01.25, 11:01:18] ~\u202fSomebody: Look here.',
        '\u200e[17.01.25, 09:48:45] Somebody: \u200e<Anhang: blob.png>'
    ])
    return wa

def makeTestHtmlFormatter():
    wa = makeTestChat()
    sb = wa.users.find("Somebody")
    wc = wacbconfig.WacbConfig(False)
    hf = wacbhtml.WacbHtmlFormatter(wa)
    hf.configure(wc["html"])
    hf.configureMe(sb)
    return hf

def makeTestApp():
    wa = makeTestChat()
    stream = io.BytesIO()
    wa.exportToZip(stream)
    app = wacbapp.App(False)
    app.open(stream)
    return app
