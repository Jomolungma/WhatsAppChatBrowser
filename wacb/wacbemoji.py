#!python

#
#    WhatsApp Chat Browser
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

"""
Emoji handling.
"""

import re
import time
import base64
import zipfile

if __package__ == "wacb":
    from . import wacbbgurl
else:
    import wacbbgurl

#
# Unicode emojis: emoji_u1f48f.png             - two people kissing
#                 emoji_u1f48f_1f3fb.png       - + emoji modifier fitzpatrick type 1-2
#
#                 emoji_u1f62e.png             - face with open mouth
#                 emoji_u1f62e_200d_1f4a8.png  - + zero-width joiner + dash symbol
#
#                 emoji_u1f3c3_1f3ff_200d_2642_fe0f_200d_27a1_fe0f.png
#                 emoji_u1f3c3_200d_2642_fe0f_200d_27a1_fe0f.png
#
#                      - 1f3c3: Runner
#                        1f3ff: Emoji modifier fitzpatrick type-6
#                         200d: zero-width joiner
#                         2642: male sign
#                         fe0f: emoji variation selector
#                         200d: zero-width joiner
#                         27a1: black rightwards arrow
#                         fe0f: emoji variation selector
#
#                 emoji_u1f926_200d_2640_fe0f.png
#
#                      - 1f926: face palm
#                         200d: zero-width joiner
#                         2640: female sign
#                         fe0f: emoji variation selector
#
#                 emoji_u23_fe0f_20e3.png
#                      -    23: number sign
#                         fe0f: emoji variation selector
#                         20e3: combining enclosing keycap
#

#
# Emoji lists from Unicode.
#

unicodeEmojiLists = [
    "https://www.unicode.org/emoji/charts/full-emoji-list.html",
    "https://www.unicode.org/emoji/charts/full-emoji-modifiers.html"
]

class SubTreeHelper:
    """
    Helper for navigating a sub-tree of a database.
    """

    def __init__(self, dataBase, subTree, path):
        self.dataBase = dataBase
        self.subTree = subTree
        self.path = path

    def __contains__(self, codePoint):
        return codePoint in self.subTree

    def __getitem__(self, codePoint):
        subPath = list(self.path)
        subPath.append(codePoint)
        return SubTreeHelper(self.dataBase, self.subTree[codePoint], subPath)

    def __len__(self):
        return len(self.path)

    def __hash__(self):
        hv = 0
        for cp in self.path:
            hv += cp
        return hv

    def __eq__(self, other):
        if len(self) != len(other):
            return False
        for i in range(len(self)):
            if self.path[i] != other.path[i]:
                return False
        return True

    def possibleContinuations(self):
        pcs = list()
        for cp in self.subTree.keys():
            if cp:
                pcs.append(cp)
        return pcs

    @property
    def isAscii(self):
        return (len(self.path) == 1) and (self.path[0] < 256)

    @property
    def isEmoji(self):
        return None in self.subTree

    @property
    def hasContinuations(self):
        pcs = self.possibleContinuations()
        return len(pcs) > 0

    @property
    def isFinal(self):
        return not self.hasContinuations

    @property
    def data(self):
        return self.subTree[None]

    @property
    def type(self):
        return self.dataBase.getType()

    @property
    def name(self):
        return self.dataBase.getName(self.path, self.data)

    @property
    def image(self):
        return self.dataBase.getImage(self.path, self.data)

    @property
    def base64(self):
        return self.dataBase.getBase64(self.path, self.data)

    @property
    def length(self):
        return len(self.path)

class Database:
    """
    Database of emojis.
    "emojis" is a tree where each node is a code point.
    Leafs have "None" in its dict of subtrees.
    Leafs can have further subtrees.
    """

    reForCodePoint = re.compile("_u?([0-9a-fA-F]+)")

    def __init__(self):
        self.count = 0
        self.emojis = dict()

    def nameToCodePoints(self, name):
        if not name.startswith("emoji_u"):
            raise KeyError
        codePoints = []
        cpMatch = Database.reForCodePoint.search(name, 5)
        while cpMatch:
            codePoint = int(cpMatch[1], 16)
            codePoints.append(codePoint)
            cpMatch = Database.reForCodePoint.search(name, cpMatch.end(0))
        return codePoints

    def codePointsToName(self, codePoints):
        fileName = "emoji_"
        first = True
        for codePoint in codePoints:
            fileName += "u" if first else "_"
            fileName += "{0:x}".format(codePoint)
            first = False
        if self.getType() == "image/png":
            fileName += ".png"
        else:
            fileName += ".svg"
        return fileName

    def __contains__(self, codePoints):
        if isinstance(codePoints, str):
            try:
                codePoints = self.nameToCodePoints(codePoints)
            except:
                return False
        elif isinstance(codePoints, int):
            codePoints = [codePoints]
        elif not isinstance(codePoints, list):
            raise TypeError
        subTree = self.emojis
        for codePoint in codePoints:
            if codePoint not in subTree:
                return False
            subTree = subTree[codePoint]
        return True

    def __getitem__(self, codePoints):
        if isinstance(codePoints, str):
            codePoints = self.nameToCodePoints(codePoints)
        elif isinstance(codePoints, int):
            codePoints = [codePoints]
        elif not isinstance(codePoints, list):
            raise TypeError
        path = []
        subTree = self.emojis
        for codePoint in codePoints:
            path.append(codePoint)
            subTree = subTree[codePoint]
        return SubTreeHelper(self, subTree, path)

    def __len__(self):
        return self.count

    def possibleContinuations(self):
        pcs = list()
        # pylint: disable=consider-iterating-dictionary
        for cp in self.emojis.keys():
            if cp:
                pcs.append(cp)
        return pcs

    @property
    def isEmoji(self):
        return None in self.emojis

    @property
    def hasContinuations(self):
        pcs = self.possibleContinuations()
        return len(pcs) > 0

    @property
    def isFinal(self):
        return not self.hasContinuations

    def getType(self):
        raise Exception("Must be implemented by a derived class.")

    def getName(self, path, emojiData):
        raise Exception("Must be implemented by a derived class.")

    def getImage(self, path, emojiData):
        raise Exception("Must be implemented by a derived class.")

    def getBase64(self, path, emojiData):
        raise Exception("Must be implemented by a derived class.")

    def addEmoji(self, codePoints, data):
        subTree = self.emojis
        for codePoint in codePoints:
            if codePoint not in subTree:
                subTree[codePoint] = dict()
            subTree = subTree[codePoint]
        subTree[None] = data
        self.count += 1

    def hasEmoji(self, codePoints):
        subTree = self[codePoints]
        return None in subTree

class ZippedDatabase(Database):
    """
    Load a set of emojis from a Zip file.
    """

    def __init__(self, fileName, subPath=None):
        super().__init__()
        self.zipFile = None
        # pylint: disable=consider-using-with
        self.zipFile = zipfile.ZipFile(fileName)
        self.fileType = None
        self.subPaths = set()
        self.scanEmojis(subPath)

    def __del__(self):
        if self.zipFile is not None:
            self.zipFile.close()
            self.zipFile = None

    def scanEmojis(self, subPath):
        for name in self.zipFile.namelist():
            emojiPos = name.find("emoji_u")
            dotPos = name.find(".", emojiPos)
            if emojiPos == -1 or dotPos == -1:
                continue
            if emojiPos > 0:
                self.subPaths.add(name[:emojiPos])
            if subPath and (subPath not in name):
                continue
            if not self.fileType:
                self.fileType = name[dotPos:]
            elif name[dotPos:] != self.fileType:
                continue
            codePoints = self.nameToCodePoints(name[emojiPos:dotPos])
            if len(codePoints) > 0:
                self.addEmoji(codePoints, {"fileName": name})

    def getType(self):
        if self.fileType == ".png":
            return "image/png"
        elif self.fileType == ".svg":
            return "image/svg+xml"
        return None

    def getName(self, path, emojiData):
        return emojiData["fileName"]

    def getImage(self, path, emojiData):
        if "imageData" in emojiData:
            return emojiData["imageData"]
        with self.zipFile.open(emojiData["fileName"]) as imgfile:
            imageData = imgfile.read()
        emojiData["imageData"] = imageData
        return imageData

    def getBase64(self, path, emojiData):
        if "base64" in emojiData:
            return emojiData["base64Data"]
        imageData = self.getImage(path, emojiData)
        base64Data = base64.b64encode(imageData).decode()
        emojiData["base64Data"] = base64Data
        return base64Data

class HtmlDatabase(Database):
    """
    Load a set of emojis from a HTML file.
    """

    reForCodePoints = re.compile("<img alt='([0-9A-Fa-fx&#;]+)'")
    reForImageData = re.compile("src=.data:image/png;base64,([A-Za-z0-9/+=]+)")
    reForCodePoint = re.compile("&#x([0-9a-fA-F]+);")

    def __init__(self, fileName=None):
        super().__init__()
        if fileName:
            self.loadFromFile(fileName)

    def loadFromFile(self, fileName):
        with open(fileName, encoding="utf-8") as file:
            htmlBody = file.read()
        self.loadFromHtml(htmlBody)

    def loadFromHtml(self, htmlBody):
        for line in htmlBody.splitlines():
            mCodePoints = HtmlDatabase.reForCodePoints.search(line)
            mImageData = HtmlDatabase.reForImageData.search(line)

            if mCodePoints and mImageData:
                name = mCodePoints[1]
                codePoints = []
                cpMatch = HtmlDatabase.reForCodePoint.search(name)
                while cpMatch:
                    codePoint = int(cpMatch[1], 16)
                    codePoints.append(codePoint)
                    cpMatch = HtmlDatabase.reForCodePoint.search(name, cpMatch.end(0))
                base64Data = mImageData[1]
                imageData = base64.b64decode(base64Data)
                if len(codePoints) > 0:
                    self.addEmoji(codePoints, {"imageData": imageData, "base64Data": base64Data})

    def getType(self):
        return "image/png"

    def getName(self, path, emojiData):
        return self.codePointsToName(path)

    def getImage(self, path, emojiData):
        return emojiData["imageData"]

    def getBase64(self, path, emojiData):
        return emojiData["base64Data"]

class ZipExporter:
    """
    Export an emoji database to a Zip file.
    """

    def __init__(self, fileName):
        self.zipFile = None
        # pylint: disable=consider-using-with
        self.zipFile = zipfile.ZipFile(fileName, "w")

    def __del__(self):
        self.close()

    def close(self):
        if self.zipFile is not None:
            self.zipFile.close()
            self.zipFile = None

    def export(self, db):
        subTree = SubTreeHelper(db, db.emojis, list())
        self.exportSubtree(subTree)

    def exportSubtree(self, subTree):
        if subTree.isEmoji:
            fileName = subTree.name
            imageData = subTree.image
            self.zipFile.writestr(fileName, imageData)

        for node in subTree.possibleContinuations():
            self.exportSubtree(subTree[node])

def exportToZip(database, zipFileName):
    ze = ZipExporter(zipFileName)
    ze.export(database)
    ze.close()

class Downloader:
    """
    Download HTML emoji databases.
    """

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.html = list()
        self.database = None

    def loadFile(self, name):
        if self.verbose:
            print("Loading \"" + name + "\" ... ", end="", flush=True)
        with open(name, encoding="utf-8") as file:
            data = file.read()
        if self.verbose:
            print("done.")
        self.html.append(data)

    def loadUrl(self, url):
        prefix = "Downloading \"" + url + "\" ... "
        downloader = wacbbgurl.BgUrlDownloader(url)

        try:
            while not downloader.done:
                if self.verbose:
                    sizeInMegabytes = len(downloader) / (1 << 20)
                    print(prefix + "{0:.1f} M".format(sizeInMegabytes), end="\r", flush=True)
                time.sleep(0.1)
        except:
            downloader.cancel()

        downloader.close()

        if not bool(downloader):
            raise Exception("Failed to download \"" + url + "\"")

        if self.verbose:
            print(prefix + "done.")

        data = downloader.get().decode()
        self.html.append(data)

    def load(self, url):
        if url[0:4] == "http":
            self.loadUrl(url)
        else:
            self.loadFile(url)

    def exportRawHtml(self, fileName):
        if self.verbose:
            print("Exporting HTML to \"" + fileName + "\" ... ", end="", flush=True)
        with open(fileName, "w", encoding="utf-8") as file:
            for data in self.html:
                file.write(data)
        if self.verbose:
            print("done.")

    def extractEmojis(self):
        if self.verbose:
            print("Extracting emojis ... ", end="", flush=True)
        self.database = HtmlDatabase()
        for data in self.html:
            self.database.loadFromHtml(data)
        if self.verbose:
            print(str(len(self.database)) + " emojis found.")

    def exportToZip(self, zipFileName):
        if not self.database:
            self.extractEmojis()
        if len(self.database) > 0:
            if self.verbose:
                print("Exporting emojis to \"" + zipFileName + "\" ... ", end="", flush=True)
            exportToZip(self.database, zipFileName)
            if self.verbose:
                print("done.")
        else:
            if self.verbose:
                print("Oops, no emojis found.")

class EmojifyMatch:
    """
    Result when the emojifier has found an emoji that could be replaced with an image.
    """

    # pos: The position where an emoji is found.
    # end: The position beyond the emoji.
    # emoji: The emoji found in the database.
    def __init__(self, pos, end, emoji):
        self.pos = pos
        self.end = end
        self.emoji = emoji

class Emojify:
    """
    Emojifier. Serches for emojis in text according to an emoji database.
    """

    pathForUrl = "emoji/"

    def __init__(self, dataBase=None):
        self.ignoreAscii = False
        self.inline = False
        self.dataBase = dataBase
        self.config = dict()

    def configure(self, configData):
        self.config = configData
        self.ignoreAscii = configData["ignoreAscii"] if "ignoreAscii" in configData else False
        self.inline = configData["inline"] if "inline" in configData else False

    @staticmethod
    def canonicalName(name):
        if name[0] == '/' and name[1:7] == Emojify.pathForUrl:
            return name[7:]
        if name.startswith(Emojify.pathForUrl):
            return name[6:]
        return name

    def url(self, emoji):
        return Emojify.pathForUrl + self.dataBase.codePointsToName(emoji.path)

    def hasFile(self, fileName):
        return Emojify.canonicalName(fileName) in self.dataBase

    def getFileSize(self, fileName):
        name = Emojify.canonicalName(fileName)
        emoji = self.dataBase[name]
        return len(emoji.image)

    def copyFile(self, fileName, outputFile, updatecb=None):
        name = Emojify.canonicalName(fileName)
        emoji = self.dataBase[name]
        outputFile.write(emoji.image)
        if updatecb:
            updatecb.update(len(emoji.image))

    @staticmethod
    def isSkinToneModifier(codePoint):
        # Emoji modifier fitzpatrick types 1..6.
        return (codePoint >= 0x1f3fb) and (codePoint <= 0x1f3ff)

    @staticmethod
    def isVariationSelector(codePoint):
        # Variation selector 1..16.
        return (codePoint >= 0xfe00) and (codePoint <= 0xfe0f)

    @staticmethod
    def isCombiningDiacriticalMark(codePoint):
        # Combining Diacritical Marks or Combining Diacritical Marks for Symbols
        isCombiningDiacriticalMark = (codePoint >= 0x300) and (codePoint <= 0x36f)
        isCombiningDiacriticalMarkForSymbol = (codePoint >= 0x20e0) and (codePoint <= 0x20ff)
        return isCombiningDiacriticalMark or isCombiningDiacriticalMarkForSymbol

    @staticmethod
    def modifiesPreviousCodePoint(codePoint):
        # Whether this code point modifies the preceding one.
        return (Emojify.isSkinToneModifier(codePoint) or
                Emojify.isVariationSelector(codePoint) or
                Emojify.isCombiningDiacriticalMark(codePoint))

    @staticmethod
    def isZWJ(codePoint):
        # Zero-width joiner.
        return codePoint == 0x200d

    def find(self, text, pos=0):
        for i in range(pos, len(text)):
            codePoint = ord(text[i])
            if codePoint in self.dataBase:
                emoji = self.get(text, i)
                if emoji and ((not emoji.isAscii) or (not self.ignoreAscii)):
                    end = self.skip(text, i)
                    return EmojifyMatch(i, end, emoji)
        return None

    def get(self, text, pos):
        subTree = self.dataBase
        for i in range(pos, len(text)):
            codePoint = ord(text[i])
            if codePoint not in subTree:
                break
            subTree = subTree[codePoint]
        return subTree if subTree.isEmoji else None

    def skip(self, text, pos):
        # First, skip over the part of the emoji that we could replace with an image.
        subTree = self.dataBase
        while pos < len(text):
            codePoint = ord(text[pos])
            if codePoint not in subTree:
                break
            subTree = subTree[codePoint]
            pos += 1
        # Next, skip over the parts of the emoji that we do not have an image for.
        while pos < len(text):
            codePoint = ord(text[pos])
            if Emojify.modifiesPreviousCodePoint(codePoint):
                # Ignore skin tone modifiers that would apply to the emoji before.
                pass
            elif Emojify.isZWJ(codePoint):
                # Ignore zero-width-joiner and the subsequent codepoint to be joined.
                pos += 1
            else:
                break
            pos += 1
        return pos

def makeEmojifier(configData):
    if ("images" not in configData) or (not configData["images"]):
        return None
    if ("dataBase" not in configData) or (not configData["dataBase"]):
        return None
    dataBase = ZippedDatabase(configData["dataBase"], configData["pathInZip"])
    emojifier = Emojify(dataBase)
    emojifier.configure(configData)
    return emojifier

def main():
    # pylint: disable=import-outside-toplevel
    import argparse

    defaultZip = "unicode-emojis.zip"
    parser = argparse.ArgumentParser(prog="Unicode Emoji Downloader")
    parser.add_argument('-u', '--url', default=[], action="append", help="Extract emojis from this URL(s) or file.")
    parser.add_argument('-r', '--raw', default=False, action=argparse.BooleanOptionalAction, help="Store the downloaded HTML file, do not extract the ZIP file.")
    parser.add_argument('-v', '--verbose', default=False, action=argparse.BooleanOptionalAction, help="Print information about progress.")
    parser.add_argument('outputFile', default=defaultZip, help="The ZIP output file to write to.")

    args = parser.parse_args()
    urls = args.url if len(args.url) > 0 else unicodeEmojiLists

    downloader = Downloader(args.verbose)

    for url in urls:
        downloader.load(url)

    if args.raw:
        downloader.exportRawHtml(args.outputFile)
    else:
        downloader.exportToZip(args.outputFile)

if __name__ == "__main__":
    main()
