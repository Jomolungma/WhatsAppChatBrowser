import io
import json
import zipfile
from wacb import wacbchat
from .wacbtesthelpers import *

#
# Example of a chat exported by the "Chat Export" feature.
#

testTgChatExportJsonChat = """{
  "name": null,
  "type": "personal_chat",
  "id": 123456,
  "messages": [
    {
      "id": 148411,
      "type": "message",
      "date": "2026-01-05T18:28:01",
      "date_unixtime": "1767624922",
      "from": "Nobody",
      "from_id": "user123456789",
      "text": "Feliz A\u00f1o Nuevo!",
      "text_entities": [
        {
          "type": "plain",
          "text": "Feliz A\u00f1o Nuevo!"
        }
      ]
    },
    {
      "id": 151196,
      "type": "message",
      "date": "2026-03-05T14:54:42",
      "date_unixtime": "1772715286",
      "from": "Me",
      "from_id": "user987654321",
      "text": "Bl\u00f6de Frage.",
      "text_entities": [
        {
          "type": "plain",
          "text": "Bl\u00f6de Frage."
        }
      ]
    },
    {
      "id": 151903,
      "type": "message",
      "date": "2026-03-26T13:59:01",
      "date_unixtime": "1774525318",
      "from": "Nobody",
      "from_id": "user123456789",
      "photo": "photos/photo_127@26-03-2026_13-59-35.jpg",
      "photo_file_size": 123456,
      "width": 960,
      "height": 1280,
      "text": "",
      "text_entities": []
    }
  ]
}
"""

#
# Example of a chat exported by the "Data Export" feature.
#

testTgDataExportJsonChat = """{
 "about": "Here is the data you requested.",
 "personal_information": {
  "user_id": 123456789,
  "first_name": "Frank",
  "last_name": "Pilhofer",
  "phone_number": "+987654321"
 },
 "chats": {
  "about": "This page lists all chats from this export.",
  "list": [
   {
    "name": "Telegram",
    "type": "personal_chat",
    "id": 147852,
    "messages": [
     {
      "id": 1234,
      "type": "message",
      "date": "2023-02-25T07:02:05",
      "date_unixtime": "1677304925",
      "from": "Telegram",
      "from_id": "user147852",
      "text": [
       {
        "type": "bold",
        "text": "Enable Two-Step Verification"
       }
      ],
      "text_entities": [
       {
        "type": "bold",
        "text": "Enable Two-Step Verification"
       }
      ]
     }
    ]
   }
  ]
 }
}
"""

class TelegramChatWithAttachments(wacbchat.TelegramJsonChat):
    def __init__(self):
        super().__init__(DummyFs())
        self.attachments = {}

    def addAttachment(self, fileName, data):
        self.fs.addAttachment(fileName, data)

def addTelegramMessagesToChat(chat, lines):
    jsonMessages = json.loads(lines)
    for jsonMessage in jsonMessages:
        chat.parseAndAddJsonMessage(jsonMessage)

def test_parseMessage():
    wa = TelegramChatWithAttachments()
    addTelegramMessagesToChat(wa, """
[
    {
      "id": 148411,
      "type": "message",
      "date": "2026-01-05T18:28:01",
      "date_unixtime": "1767624922",
      "from": "Nobody",
      "from_id": "user123456789",
      "text": "Feliz A\u00f1o Nuevo!",
      "text_entities": [
        {
          "type": "plain",
          "text": "Feliz A\u00f1o Nuevo!"
        }
      ]
    },
    {
      "id": 151196,
      "type": "message",
      "date": "2026-03-05T14:54:42",
      "date_unixtime": "1772715286",
      "from": "Me",
      "from_id": "user987654321",
      "text": "Bl\u00f6de Frage.",
      "text_entities": [
        {
          "type": "plain",
          "text": "Bl\u00f6de Frage."
        }
      ]
    }
]
    """)
    assert wa[0].isUserMessage and wa[0].user == "Nobody"
    assert wa[1].isUserMessage and wa[1].user == "Me"

def test_parseMessageWithAttachment():
    wa = TelegramChatWithAttachments()
    wa.addAttachment("photos/photo_127@26-03-2026_13-59-35.jpg", "Dummy Data")
    addTelegramMessagesToChat(wa, """
[
    {
      "id": 151903,
      "type": "message",
      "date": "2026-03-26T13:59:01",
      "date_unixtime": "1774525318",
      "from": "Nobody",
      "from_id": "user123456789",
      "photo": "photos/photo_127@26-03-2026_13-59-35.jpg",
      "photo_file_size": 123456,
      "width": 960,
      "height": 1280,
      "text": "",
      "text_entities": []
    }
]
    """)
    assert wa[0].isUserMessage and wa[0].user == "Nobody"
    assert wa[0].hasAttachment

def test_parseMessageWithEmbeddedLink():
    wa = TelegramChatWithAttachments()
    addTelegramMessagesToChat(wa, """
[
    {
      "id": 151196,
      "type": "message",
      "date": "2026-03-05T14:54:42",
      "date_unixtime": "1772715286",
      "from": "Me",
      "from_id": "user987654321",
      "text": [
        "Now on your playlist: ",
        {
          "type": "link",
          "text": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }
      ],
      "text_entities": [
        {
          "type": "plain",
          "text": "Now on your playlist: "
        },
        {
          "type": "link",
          "text": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }
      ]
    }
]
    """)
    assert wa[0].isUserMessage and wa[0].user == "Me"
    assert wa[0].text.startswith("Now on your playlist: https")

def testFromDirectory(tmp_path):
    tmpDir = tmp_path / "subdir"
    tmpDir.mkdir()
    tmpFile = tmpDir / "result.json"
    tmpFile.write_text(testTgChatExportJsonChat, encoding="utf-8")
    imgDir = tmpDir / "photos"
    imgDir.mkdir(parents=True)
    imgFile = imgDir / "photo_127@26-03-2026_13-59-35.jpg"
    imgFile.write_text("Dummy Data")
    wa = wacbchat.openChat(tmpFile)
    assert len(wa) == 3
    assert wa[2].hasAttachment

def testFromZippedChat(tmp_path):
    tmpZip = tmp_path / "zipped_chat.zip"
    with zipfile.ZipFile(tmpZip, "w") as zFile:
        zFile.writestr("subdir/result.json", testTgChatExportJsonChat)
        zFile.writestr("subdir/photos/photo_127@26-03-2026_13-59-35.jpg", "Dummy Data")
    wa = wacbchat.openChat(tmpZip)
    assert len(wa) == 3
    assert wa[2].hasAttachment

def testFromTextStream():
    stream = io.StringIO(testTgChatExportJsonChat)
    wa = wacbchat.openChat(stream)
    assert len(wa) == 3

def testFromDataExportStream():
    stream = io.StringIO(testTgDataExportJsonChat)
    wa = wacbchat.openChat(stream)
    assert len(wa) == 1
