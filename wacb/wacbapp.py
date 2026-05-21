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

import zipfile
import urllib.parse
from pathlib import Path

if __package__ == "wacb":
    from . import wacbchat
    from . import wacbhtml
    from . import wacbhttp
    from . import wacbemoji
    from . import wacbconfig
else:
    import wacbchat
    import wacbhtml
    import wacbhttp
    import wacbemoji
    import wacbconfig

class QuietDownloadStatistics:
    def start(self, fileName):
        return self

    def oops(self, message):
        pass

    def update(self, bytesServed):
        pass

    def finish(self, success):
        pass

class ConsoleDownloadStatisticsHelper:
    def __init__(self, fileName):
        self.fileName = fileName

    def update(self, bytesServed):
        pass

    def finish(self, success):
        successOrFailure = "finished" if success else "failed"
        print("Download of \"" + self.fileName + "\" " + successOrFailure + ".")

class ConsoleDownloadStatistics:
    def start(self, fileName):
        print("Starting download of \"" + fileName + "\".")
        return ConsoleDownloadStatisticsHelper(fileName)

    def oops(self, message):
        print(message)

#
# This class is the glue between the message container, which stores messages,
# the HTML formatter, which is responsible for the conversion of messages to
# HTML, and the HTTP request handler, wich serves requests from the HTTP server.
#

class HttpHtmlGlue:
    def __init__(self, messageContainer, htmlFormatter, emojifier=None):
        self.messageContainer = messageContainer
        self.htmlFormatter = htmlFormatter
        self.emojifier = emojifier
        self.statisticsCollector = QuietDownloadStatistics()

    def setStatisticsCollector(self, collector):
        self.statisticsCollector = collector

    def getHttpHeaders(self, path):
        path = urllib.parse.unquote(path)
        if path == "/":
            return 301, {"Location": "index.html"}

        if not self.hasFile(path):
            self.statisticsCollector.oops("Requested file \"" + path + "\" is not available.")
            return 404, None

        contentType = self.getContentTypeFromFileName(path)
        return 200, {"Content-Type": contentType}

    def getFile(self, path, wfile):
        path = urllib.parse.unquote(path)
        updatecb = self.statisticsCollector.start(path)
        try:
            if self.htmlFormatter.hasFile(path):
                self.htmlFormatter.copyFile(path, wfile, updatecb)
            elif self.messageContainer.hasFile(path):
                self.messageContainer.copyFile(path, wfile, updatecb)
            elif self.emojifier and self.emojifier.hasFile(path):
                self.emojifier.copyFile(path, wfile, updatecb)
            else:
                updatecb.finish(False)
                raise Exception("Oops: \"" + path + "\".")
            updatecb.finish(True)
        except ConnectionAbortedError:
            updatecb.finish(False)
        except ConnectionResetError:
            updatecb.finish(False)

    def hasFile(self, path):
        if self.htmlFormatter.hasFile(path):
            return True
        elif self.messageContainer.hasFile(path):
            return True
        elif self.emojifier and self.emojifier.hasFile(path):
            return True
        return False

    extToContentTypeMap = {
        "html": "text/html; charset=utf-8",
        "css":  "text/css; charset=utf-8",
        "jpeg": "image/jpeg",
        "jpg":  "image/jpeg",
        "png":  "image/png",
        "webp": "image/webp",
        "svg":  "image/svg+xml",
        "opus": "audio/ogg",
        "mp3":  "audio/mpeg",
        "m4a":  "audio/mp4",
        "mp4":  "video/mp4",
        "mov":  "video/quicktime",
        "pdf":  "application/pdf"
    }

    def getContentTypeFromFileName(self, fileName):
        lastDot = fileName.rfind(".")
        if lastDot == -1:
            return None
        ext = fileName[lastDot+1:]
        if ext in HttpHtmlGlue.extToContentTypeMap:
            return HttpHtmlGlue.extToContentTypeMap[ext]
        return "application/octet-stream"

#
# This class does everything but the UI.
#

class App:
    def __init__(self, useConfigFile=True, configFile=None):
        self.running = False
        self.messageContainer = None
        self.filteredMessages = None
        self.htmlFormatter = None
        self.emojifier = None
        self.httpHtmlGlue = None
        self.httpServerManager = None
        self.fileName = None
        self.statisticsCollector = None
        self.title = None
        self.config = wacbconfig.WacbConfig(useConfigFile, configFile)

    def __del__(self):
        self.stop()

    @property
    def url(self):
        return self.httpServerManager.url

    @property
    def chat(self):
        return self.filteredMessages if self.filteredMessages else self.messageContainer

    @property
    def formatter(self):
        if self.htmlFormatter:
            return self.htmlFormatter
        self.emojifier = wacbemoji.makeEmojifier(self.config["emoji"])
        self.htmlFormatter = wacbhtml.WacbHtmlFormatter(self.chat)
        self.htmlFormatter.configure(self.config["html"])
        self.htmlFormatter.configureUserMap(self.config["userNameMap"])
        if ("me" in self.config) and (len(self.config["me"]) > 0) and (self.config["me"][0] != self.config["nobody"]):
            self.htmlFormatter.configureMe(self.config["me"][0])
        if self.title:
            self.htmlFormatter.configureTitle(self.title)
        if self.emojifier:
            self.htmlFormatter.configureEmojifier(self.emojifier)
        return self.htmlFormatter
        
    def setStatisticsCollector(self, collector):
        self.statisticsCollector = collector

    def configure(self, configData):
        self.config.load()
        self.config.merge(configData)

    def saveConfiguration(self):
        self.config.save()

    def open(self, files):
        self.stop()
        self.fileName = None
        self.messageContainer = wacbchat.openChat(files)
        self.fileName = self.messageContainer.fileName

    def merge(self, files):
        newMessages = wacbchat.openChat(files)
        self.stop()
        self.fileName = None
        oldMessages = self.messageContainer
        if oldMessages:
            self.messageContainer = wacbchat.MergedChat([oldMessages, newMessages])
        else:
            self.messageContainer = newMessages
        self.fileName = self.messageContainer.fileName

    def close(self):
        self.stop()
        self.fileName = None
        self.messageContainer = None
        self.filteredMessages = None

    def filterByDateRange(self, fromDate, toDate):
        if not fromDate and not toDate:
            self.resetFilter()
        self.filteredMessages = wacbchat.FilteredByTime(self.messageContainer, fromDate, toDate)

    def currentDateRangeFilter(self):
        if not self.filteredMessages:
            return None, None
        return self.filteredMessages.fromDate, self.filteredMessages.toDate

    def resetFilter(self):
        self.filteredMessages = None

    def startHttpServer(self):
        if self.httpServerManager:
            return
        self.httpBackend = HttpHtmlGlue(self.chat, self.formatter, self.emojifier)
        if self.statisticsCollector:
            self.httpBackend.setStatisticsCollector(self.statisticsCollector)
        self.httpServerManager = wacbhttp.WacbHttpServerManager(self.httpBackend)
        self.httpServerManager.configure(self.config["http"])
        self.httpServerManager.start()
        
    def start(self):
        if not self.messageContainer:
            return
        self.running = True
        self.startHttpServer()

    def stop(self):
        if self.httpServerManager:
            self.httpServerManager.stop()
            self.httpServerManager = None
        self.htmlFormatter = None
        self.emojifier = None
        self.running = False

    # Note: fileName can be a file name or a file-like object.
    def exportToZip(self, fileName):
        with zipfile.ZipFile(fileName, "w") as zFile:
            for url in self.formatter.enumerateUrls():
                with zFile.open(url, 'w') as aFile:
                    self.formatter.copyFile(url, aFile)
            for attachment in self.formatter.linkedAttachments:
                with zFile.open(attachment, 'w') as aFile:
                    self.chat.copyFile(attachment, aFile)
            for emoji in self.formatter.linkedEmojis:
                with zFile.open(self.emojifier.url(emoji), 'w') as aFile:
                    aFile.write(emoji.image)

    def exportToDir(self, dirName):
        dirPath = Path(dirName)
        if not dirPath.is_dir():
            dirPath.mkdir()
        children = [str(f) for f in dirPath.iterdir()]
        if len(children) > 0:
            raise Exception("Oops, \"" + str(dirName) + "\" is not empty.")
        for url in self.formatter.enumerateUrls():
            with open(dirPath / url, 'wb') as aFile:
                self.formatter.copyFile(url, aFile)
        for attachment in self.formatter.linkedAttachments:
            with open(dirPath / attachment, 'wb') as aFile:
                self.chat.copyFile(attachment, aFile)
        if len(self.formatter.linkedEmojis) > 0:
            emojiPath = dirPath / "emoji"
            emojiPath.mkdir()
            for emoji in self.formatter.linkedEmojis:
                with open(dirPath / self.emojifier.url(emoji), 'wb') as aFile:
                    aFile.write(emoji.image)

#
# Allow to run from the command line.
#

def run(chatFiles=None, title=None, useConfigFile=True, configFile=None, verbosity=0):
    import time
    app = App(useConfigFile, configFile)
    if verbosity > 0:
        app.setStatisticsCollector(ConsoleDownloadStatistics())
    app.open(chatFiles)
    if title:
        app.title = title
    app.start()
    print("Running at \"" + app.url + "\".")
    try:
        while True:
            time.sleep(1000)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("Oops: " + str(e))
    print("Stopping.")
    app.stop()
    app.close()

def exportAsHtml(zipFile=None, chatFiles=None, title=None, useConfigFile=True, configFile=None, verbosity=0):
    app = App(useConfigFile, configFile)
    app.open(chatFiles)
    if title:
        app.title = title
    app.exportToZip(zipFile)
    app.close()

if __name__ == "__main__":
    if __package__ == "wacb":
        from . import wacb
    else:
        import wacb
    wacb.run(False)
