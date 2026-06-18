import io
import json
import zipfile
from wacb import wacbchat
from .wacbtesthelpers import *

testWaceJsonChat = """{
  "123456789098765432@g.us": {
    "name": "Group Chat Name",
    "type": "ios",
    "media_base": "AppDomainGroup-group.net.whatsapp.WhatsApp.shared/",
    "messages": {
      "148411": {
        "from_me": false,
        "timestamp": 1767624922,
        "time": "16:55",
        "media": false,
        "key_id": "random number",
        "meta": false,
        "data": "Feliz A\u00f1o Nuevo!<br>",
        "sender": "Nobody",
        "safe": false,
        "mime": null,
        "message_type": 0,
        "received_timestamp": "2026/01/05 18:28",
        "read_timestamp": null,
        "reply": null,
        "quoted_data": null,
        "caption": null,
        "thumb": null,
        "sticker": false,
        "reactions": {}
      },
      "151196": {
        "from_me": true,
        "timestamp": 1772715286.523911,
        "time": "14:54",
        "media": false,
        "key_id": "random number",
        "meta": false,
        "data": "Bl\u00f6de Frage.",
        "sender": null,
        "safe": false,
        "mime": null,
        "message_type": 0,
        "received_timestamp": "2026/03/05 14:54",
        "read_timestamp": null,
        "reply": null,
        "quoted_data": null,
        "caption": null,
        "thumb": null,
        "sticker": false,
        "reactions": {}
      },
      "151903": {
        "from_me": false,
        "timestamp": 1774525318,
        "time": "13:41",
        "media": true,
        "key_id": "random-number",
        "meta": false,
        "data": "Message/Media/random-number@g.us/a/b/abc10038-ee07-4aee-befa-54a38b60a8a8.jpg",
        "sender": "Nobody",
        "safe": false,
        "mime": "image/jpeg",
        "message_type": 1,
        "received_timestamp": "2026/03/26 13:59",
        "read_timestamp": null,
        "reply": null,
        "quoted_data": null,
        "caption": null,
        "thumb": null,
        "sticker": false,
        "reactions": {}
      }
    }
  }
}
"""

class WaceChatWithAttachments(wacbchat.WaceJsonChat):
    def __init__(self):
        super().__init__(DummyFs())
        self.attachments = {}

    def addAttachment(self, fileName, data):
        self.fs.addAttachment(fileName, data)

def addWaceMessagesToChat(chat, lines):
    jsonData = json.loads(lines)
    for messageId in jsonData.keys():
        chat.parseAndAddJsonMessage(jsonData[messageId])

def test_parseSystemMessage():
    wa = WaceChatWithAttachments()
    addWaceMessagesToChat(wa, """
{
    "148417": {
        "from_me": false,
        "timestamp": 1767624698,
        "time": "16:51",
        "media": false,
        "key_id": "some magic number",
        "meta": true,
        "data": "The group name changed to some magic number",
        "sender": null,
        "safe": false,
        "mime": null,
        "message_type": 6,
        "received_timestamp": null,
        "read_timestamp": null,
        "reply": null,
        "quoted_data": null,
        "caption": null,
        "thumb": null,
        "sticker": false,
        "reactions": {}
      }
}
    """)
    assert wa[0].isSystemMessage

def test_parseMessage():
    wa = WaceChatWithAttachments()
    addWaceMessagesToChat(wa, """
{
      "148411": {
        "from_me": false,
        "timestamp": 1767624922,
        "time": "16:55",
        "media": false,
        "key_id": "random number",
        "meta": false,
        "data": "Feliz A\u00f1o Nuevo!<br>",
        "sender": "Nobody",
        "safe": false,
        "mime": null,
        "message_type": 0,
        "received_timestamp": "2026/01/05 18:28",
        "read_timestamp": null,
        "reply": null,
        "quoted_data": null,
        "caption": null,
        "thumb": null,
        "sticker": false,
        "reactions": {}
      },
      "151196": {
        "from_me": true,
        "timestamp": 1772715286.523911,
        "time": "14:54",
        "media": false,
        "key_id": "random number",
        "meta": false,
        "data": "Bl\u00f6de Frage.",
        "sender": null,
        "safe": false,
        "mime": null,
        "message_type": 0,
        "received_timestamp": "2026/03/05 14:54",
        "read_timestamp": null,
        "reply": null,
        "quoted_data": null,
        "caption": null,
        "thumb": null,
        "sticker": false,
        "reactions": {}
      }
}
    """)
    assert wa[0].isUserMessage and wa[0].user == "Nobody"
    assert wa[1].isUserMessage and wa[1].user == "Me"

def test_parseMessageWithAttachment():
    wa = WaceChatWithAttachments()
    wa.addAttachment("Message/Media/random-number@g.us/a/b/abc10038-ee07-4aee-befa-54a38b60a8a8.jpg", "Dummy Data")
    addWaceMessagesToChat(wa, """
{
      "151903": {
        "from_me": false,
        "timestamp": 1774525318,
        "time": "13:41",
        "media": true,
        "key_id": "random-number",
        "meta": false,
        "data": "Message/Media/random-number@g.us/a/b/abc10038-ee07-4aee-befa-54a38b60a8a8.jpg",
        "sender": "Nobody",
        "safe": false,
        "mime": "image/jpeg",
        "message_type": 1,
        "received_timestamp": "2026/03/26 13:59",
        "read_timestamp": null,
        "reply": null,
        "quoted_data": null,
        "caption": null,
        "thumb": null,
        "sticker": false,
        "reactions": {}
      }
}
    """)
    assert wa[0].isUserMessage and wa[0].user == "Nobody"
    assert wa[0].hasAttachment

def testFromDirectory(tmp_path):
    tmpDir = tmp_path / "subdir"
    tmpDir.mkdir()
    tmpFile = tmpDir / "result.json"
    tmpFile.write_text(testWaceJsonChat, encoding="utf-8")
    imgDir = tmpDir / "AppDomainGroup-group.net.whatsapp.WhatsApp.shared/Message/Media/random-number@g.us/a/b"
    imgDir.mkdir(parents=True)
    imgFile = imgDir / "abc10038-ee07-4aee-befa-54a38b60a8a8.jpg"
    imgFile.write_text("Dummy Data")
    wa = wacbchat.openChat(tmpFile)
    assert len(wa) == 3
    assert wa[2].hasAttachment

def testFromZippedChat(tmp_path):
    tmpZip = tmp_path / "zipped_chat.zip"
    with zipfile.ZipFile(tmpZip, "w") as zFile:
        zFile.writestr("subdir/result.json", testWaceJsonChat)
        zFile.writestr("subdir/AppDomainGroup-group.net.whatsapp.WhatsApp.shared/Message/Media/random-number@g.us/a/b/abc10038-ee07-4aee-befa-54a38b60a8a8.jpg", "Dummy Data")
    wa = wacbchat.openChat(tmpZip)
    assert len(wa) == 3
    assert wa[2].hasAttachment

def testFromTextStream(tmp_path):
    stream = io.StringIO(testWaceJsonChat)
    wa = wacbchat.openChat(stream)
    assert len(wa) == 3
