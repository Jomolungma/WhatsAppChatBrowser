import io
import base64
import html.parser
import html5lib
from wacb import wacbchat
from wacb import wacbhtml
from wacb import wacbemoji
from .wacbtesthelpers import *

class CollectHtmlTags(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = dict()

    def handle_starttag(self, tag, attrs):
        if not tag in self.tags:
            self.tags[tag] = list()
        ad = dict()
        for attr in attrs:
            ad[attr[0]] = attr[1]
        self.tags[tag].append(ad)

def test_formatMessages():
    wa = makeTestChat()
    hf = wacbhtml.WacbHtmlFormatter(wa)
    for msg in wa:
        html = hf.formatMessage(msg)

def test_inlineEmoji():
    wa = ChatWithAttachments()
    addMessagesToChat(wa, [
        '[09.01.25, 15:48:14] Nobody: Just#Testing.'
    ])
    em = EmojiDatabaseForTest()
    em.addEmoji([35], getPngBlob())
    ej = wacbemoji.Emojify(em)
    hf = wacbhtml.WacbHtmlFormatter(wa)
    hf.configureEmojifier(ej)
    # Emoji not inline: expecting link.
    html = hf.formatMessage(wa[0])
    cht = CollectHtmlTags()
    cht.feed(html)
    assert "img" in cht.tags and len(cht.tags["img"]) == 1
    src = cht.tags["img"][0]["src"]
    assert src.startswith("emoji/")
    # Inline emoji: expecting data
    ej.inline = True
    html = hf.formatMessage(wa[0])
    cht = CollectHtmlTags()
    cht.feed(html)
    assert "img" in cht.tags and len(cht.tags["img"]) == 1
    src = cht.tags["img"][0]["src"]
    assert src.startswith("data:")

def checkHtmlPage(hf, url):
    out = io.BytesIO()
    assert hf.hasFile(url)
    hf.copyFile(url, out)
    hp = html5lib.HTMLParser(strict=True)
    hp.parse(out)
    
def test_singleDocument():
    hf = makeTestHtmlFormatter()
    checkHtmlPage(hf, "/index.html")

def test_annualDocuments():
    hf = makeTestHtmlFormatter()
    hf.config["showAs"] = "Annual"
    for url in hf.enumerateUrls():
        if not url.endswith(".html"):
            continue
        checkHtmlPage(hf, "/" + url)

def test_monthlyDocuments():
    hf = makeTestHtmlFormatter()
    hf.config["showAs"] = "Monthly"
    for url in hf.enumerateUrls():
        if not url.endswith(".html"):
            continue
        checkHtmlPage(hf, "/" + url)
