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

import datetime
import webbrowser
import threading
import tkinter
import tkinter.filedialog
from tkinter import ttk, font
from pathlib import Path

if __package__ == "wacb":
    from . import wacbchat
    from . import wacbapp
    from . import wacbemoji
    from . import wacbbgurl
    from . import wacbcss
else:
    import wacbchat
    import wacbapp
    import wacbemoji
    import wacbbgurl
    import wacbcss

try:
    import pyperclip
    havePyperClip = True
except:
    havePyperClip = False

try:
    import tkinterdnd2
    haveDnd = True
except:
    haveDnd = False

#
# Download statistics collector.
#

class DownloadStatisticsCollector:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        with self.lock:
            self.totalDownloads = 0
            self.activeDownloads = 0
            self.successfulDownloads = 0
            self.failedDownloads = 0
            self.bytesServed = 0
        
    def start(self, fileName):
        with self.lock:
            self.activeDownloads += 1
        return self

    def update(self, bytesServed):
        with self.lock:
            self.bytesServed += bytesServed

    def finish(self, success):
        with self.lock:
            self.activeDownloads -= 1
            self.totalDownloads += 1
            if success:
                self.successfulDownloads += 1
            else:
                self.failedDownloads += 1

#
# Top-level window to select an emoji file.
#

class EmojiSelector(tkinter.Toplevel):
    def __init__(self, parent, currentFileName=None, currentPathInZip=None):
        super().__init__(parent.top)
        self.success = False
        self.parent = parent
        self.top = self.parent.top
        self.fileName = tkinter.StringVar()
        self.pathInZip = tkinter.StringVar()
        self.statusMessage = tkinter.StringVar()
        self.database = None
        self.widgets = dict()
        self.createWidgets()
        self.statusMessage.set("Browse for an emoji database.")
        if currentPathInZip:
            self.pathInZip.set(currentPathInZip)
        if currentFileName and len(currentFileName) > 0:
            try:
                self.open(currentFileName)
                self.fileName.set(currentFileName)
            except:
                pass

    def __bool__(self):
        return self.success

    def createWidgets(self):
        self.title("Select Emoji Database")

        fileFrame = ttk.Frame(self)
        browseButton = ttk.Button(fileFrame, text="Browse", width=12, command=self.browseButtonPressed)
        fileNameLabel = ttk.Entry(fileFrame, width=40, textvariable=self.fileName)
        browseButton.pack(side="left", padx=10)
        fileNameLabel.pack(side="left", fill="x", expand="yes", padx=10)
        fileFrame.pack(side="top", fill="x")
        fileNameLabel.bind("<Return>", self.fileNameEnterPressed)

        pathFrame = ttk.Frame(self)
        subPathFrame = ttk.Frame(pathFrame)
        subPathLabel = ttk.Label(subPathFrame, text="Sub-Path", width=12, font=self.parent.defaultFont)
        subPathCombo = ttk.Combobox(subPathFrame, width=40, values=[], textvariable=self.pathInZip)
        subPathLabel.pack(side="left", padx=10)
        subPathCombo.pack(side="left", fill="x", expand="yes", padx=10)
        subPathFrame.pack(side="top", fill="x")
        pathFrame.pack(side="top", fill="x", padx=10, pady=5)
        self.widgets["subPathCombo"] = subPathCombo

        buttonFrame = ttk.Frame(self)
        buttonFrameInt = ttk.Frame(buttonFrame)
        okButton = ttk.Button(buttonFrameInt, text="OK", width=12, command=self.okButtonPressed, state="disabled")
        cancelButton = ttk.Button(buttonFrameInt, text="Cancel", width=12, command=self.cancelButtonPressed)
        okButton.pack(side="left", padx=10)
        cancelButton.pack(side="left", padx=10)
        buttonFrameInt.pack(side="top", expand="yes", anchor="c")
        buttonFrame.pack(side="top", padx=10, pady=5)
        self.widgets["okButton"] = okButton

        statusFrame = ttk.Frame(self)
        statusLabel = ttk.Label(statusFrame, textvariable=self.statusMessage, relief="sunken", width=40)
        statusLabel.pack(side="left", fill="x", expand="yes")
        statusFrame.pack(side="top", fill="x")

    def open(self, fileName):
        self.widgets["okButton"].state(["disabled"])
        self.database = wacbemoji.ZippedDatabase(fileName)
        pathsInZip = list(self.database.subPaths)
        pathsInZip.sort()
        widget = self.widgets["subPathCombo"]
        currentPath = widget.get()
        widget.configure(values=pathsInZip)
        if len(pathsInZip) > 0:
            if currentPath not in pathsInZip:
                suggestedIndex = 0
                for i in range(len(pathsInZip)):
                    if "/32/" in pathsInZip[i]:
                        suggestedIndex = i
                widget.current(suggestedIndex)
        else:
            widget.set("")    
        self.statusMessage.set(str(len(self.database)) + " emojis loaded.")
        self.widgets["okButton"].state(["!disabled"])

    def browseButtonPressed(self):
        fileTypeSuggestion = [["ZIP Files", "*.zip"]]
        fileName = tkinter.filedialog.askopenfilename(filetypes=fileTypeSuggestion)
        if fileName == "":
            return
        self.fileName.set(str(Path(fileName)))
        self.open(self.fileName.get())

    def fileNameEnterPressed(self, widget):
        self.open(self.fileName.get())

    def okButtonPressed(self):
        self.success = True
        self.destroy()

    def cancelButtonPressed(self):
        self.success = False
        self.destroy()

    def run(self):
        self.grab_set()
        self.parent.top.wait_window(self)

#
# Top-level window for downloading Unicode emojis.
#

class EmojiDownloader(tkinter.Toplevel):
    updatePeriodMs = 100

    def __init__(self, parent):
        super().__init__(parent.top)
        self.success = False
        self.downloading = False
        self.downloader = None
        self.canceled = False
        self.parent = parent
        self.top = self.parent.top
        self.useUrl1 = tkinter.BooleanVar()
        self.useUrl2 = tkinter.BooleanVar()
        self.url1 = tkinter.StringVar()
        self.url2 = tkinter.StringVar()
        self.statusMessage = tkinter.StringVar()
        self.database = None
        self.fileName = tkinter.StringVar()
        self.pathInZip = tkinter.StringVar()
        self.widgets = dict()
        self.createWidgets()
        if len(wacbemoji.unicodeEmojiLists) >= 2:
            self.useUrl1.set(True)
            self.useUrl2.set(True)
            self.url1.set(wacbemoji.unicodeEmojiLists[0])
            self.url2.set(wacbemoji.unicodeEmojiLists[1])

    def __bool__(self):
        return self.success

    def createWidgets(self):
        self.title("Download Emoji Database")

        url1Frame = ttk.Frame(self)
        url1Button = ttk.Checkbutton(url1Frame, variable=self.useUrl1)
        url1Url = ttk.Entry(url1Frame, width=40, textvariable=self.url1)
        url1Button.pack(side="left", padx=10)
        url1Url.pack(side="left", fill="x", expand="yes", padx=10)
        url1Frame.pack(side="top", fill="x")

        url2Frame = ttk.Frame(self)
        url2Button = ttk.Checkbutton(url2Frame, variable=self.useUrl2)
        url2Url = ttk.Entry(url2Frame, width=40, textvariable=self.url2)
        url2Button.pack(side="left", padx=10)
        url2Url.pack(side="left", fill="x", expand="yes", padx=10)
        url2Frame.pack(side="top", fill="x")

        buttonFrame = ttk.Frame(self)
        buttonFrameInt = ttk.Frame(buttonFrame)
        downloadButton = ttk.Button(buttonFrameInt, text="Download", width=12, command=self.downloadButtonPressed)
        saveAsButton = ttk.Button(buttonFrameInt, text="Save As", width=12, command=self.saveAsButtonPressed, state="disabled")
        cancelButton = ttk.Button(buttonFrameInt, text="Cancel", width=12, command=self.cancelButtonPressed)
        downloadButton.pack(side="left", padx=10)
        saveAsButton.pack(side="left", padx=10)
        cancelButton.pack(side="left", padx=10)
        buttonFrameInt.pack(side="top", expand="yes", anchor="c")
        buttonFrame.pack(side="top", padx=10, pady=5)
        self.widgets["downloadButton"] = downloadButton
        self.widgets["saveAsButton"] = saveAsButton

        statusFrame = ttk.Frame(self)
        statusLabel = ttk.Label(statusFrame, textvariable=self.statusMessage, relief="sunken", width=40)
        statusLabel.pack(side="left", fill="x", expand="yes")
        statusFrame.pack(side="top", fill="x")

    def updateButtonState(self, name, state):
        stateValue = "!disabled" if state else "disabled"
        self.widgets[name].state([stateValue])

    def updateWidgets(self):
        self.updateButtonState("downloadButton", not self.downloading)
        self.updateButtonState("saveAsButton", bool(self.database))

    def updateDownload(self):
        if self.canceled:
            self.destroy()
            return
        if self.downloader == None:
            return
        if not self.downloader.done:
            currentName = self.downloader.getCurrentName()
            sizeInBytes = self.downloader.getCurrentBytes()
            sizeInMegabytes = sizeInBytes / (1 << 20)
            self.statusMessage.set("Downloading \"{0}\" ... {1:.1f} M".format(currentName, sizeInMegabytes))
            self.top.after(EmojiDownloader.updatePeriodMs, self.updateDownload)
            return
        self.downloading = False

    def downloadButtonPressed(self):
        urls = list()
        if self.useUrl1.get():
            urls.append(self.url1.get())
        if self.useUrl2.get():
            urls.append(self.url2.get())

        if len(urls) == 0:
            self.downloading = False
            return

        self.downloading = True
        self.downloader = wacbbgurl.BgUrlsDownloader(urls, self.downloadFinished)
        self.top.after(EmojiDownloader.updatePeriodMs, self.updateDownload)
        self.updateWidgets()

    def downloadFinished(self):
        if self.canceled:
            self.destroy()
        self.downloading = False
        if not bool(self.downloader):
            self.updateWidgets()
            self.statusMessage.set("Download failed.")
            return
        self.database = wacbemoji.HtmlDatabase()
        for download in self.downloader:
            self.database.loadFromHtml(download.data.decode())
        self.updateWidgets()
        self.statusMessage.set(str(len(self.database)) + " emojis loaded.")

    def saveAsButtonPressed(self):
        defaultExtension = ".zip"
        fileTypeSuggestion = [["ZIP Files", "*.zip"]]
        fileName = tkinter.filedialog.asksaveasfilename(filetypes=fileTypeSuggestion, defaultextension=defaultExtension)
        if fileName == "":
            return
        self.fileName.set(str(Path(fileName)))
        self.pathInZip.set("")
        try:
            wacbemoji.exportToZip(self.database, self.fileName.get())
        except:
            self.statusMessage.set("Saving as \"" + self.fileName.get() + "\" failed.")
            return
        self.success = True
        self.destroy()

    def cancelButtonPressed(self):
        self.success = False
        self.canceled = True
        if not self.downloading:
            self.destroy()
        else:
            self.downloader.cancel()

    def run(self):
        self.grab_set()
        self.parent.top.wait_window(self)

#
# Top-level window for HTTP configuration.
#

class HttpConfigurator(tkinter.Toplevel):
    def __init__(self, parent, currentHostName=None, currentPortNumber=None):
        super().__init__(parent.top)
        self.success = False
        self.parent = parent
        self.top = self.parent.top
        self.hostName = tkinter.StringVar()
        self.portNumber = tkinter.StringVar()
        self.statusMessage = tkinter.StringVar()
        self.widgets = dict()
        self.createWidgets()
        self.statusMessage.set("Edit HTTP Server configuration.")
        if currentHostName:
            self.hostName.set(currentHostName)
        else:
            self.hostName.set("localhost")
        if currentPortNumber:
            self.portNumber.set(str(currentPortNumber))
        else:
            self.portNumber.set("0")

    def __bool__(self):
        return self.success

    def createWidgets(self):
        self.title("HTTP Server configuration")

        hostNameFrame = ttk.Frame(self)
        hostNameLabel = ttk.Label(hostNameFrame, text="Host Name", width=12, font=self.parent.defaultFont)
        hostNameEntry = ttk.Entry(hostNameFrame, width=30, textvariable=self.hostName)
        hostNameLabel.pack(side="left", padx=10)
        hostNameEntry.pack(side="left", fill="x", expand="yes", padx=10)
        hostNameFrame.pack(side="top", fill="x")

        portNumberFrame = ttk.Frame(self)
        portNumberLabel = ttk.Label(portNumberFrame, text="Port Number", width=12, font=self.parent.defaultFont)
        portNumberEntry = ttk.Entry(portNumberFrame, width=30, textvariable=self.portNumber)
        portNumberLabel.pack(side="left", padx=10)
        portNumberEntry.pack(side="left", fill="x", expand="yes", padx=10)
        portNumberFrame.pack(side="top", fill="x")

        buttonFrame = ttk.Frame(self)
        buttonFrameInt = ttk.Frame(buttonFrame)
        okButton = ttk.Button(buttonFrameInt, text="OK", width=12, command=self.okButtonPressed)
        cancelButton = ttk.Button(buttonFrameInt, text="Cancel", width=12, command=self.cancelButtonPressed)
        okButton.pack(side="left", padx=10)
        cancelButton.pack(side="left", padx=10)
        buttonFrameInt.pack(side="top", expand="yes", anchor="c")
        buttonFrame.pack(side="top", padx=10, pady=5)

        statusFrame = ttk.Frame(self)
        statusLabel = ttk.Label(statusFrame, textvariable=self.statusMessage, relief="sunken", width=40)
        statusLabel.pack(side="left", fill="x", expand="yes")
        statusFrame.pack(side="top", fill="x")

    def okButtonPressed(self):
        self.success = True
        self.destroy()

    def cancelButtonPressed(self):
        self.success = False
        self.destroy()

    def run(self):
        self.grab_set()
        self.parent.top.wait_window(self)

#
# Top-level window for filtering by date.
#

class FilterByDate(tkinter.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent.top)
        self.success = False
        self.parent = parent
        self.top = self.parent.top
        self.fromDate = None
        self.toDate = None
        self.fromDateVar = tkinter.StringVar()
        self.toDateVar = tkinter.StringVar()
        self.statusMessage = tkinter.StringVar()
        self.app = app
        self.widgets = dict()
        self.createWidgets()
        self.updateFromAndToDates()
        self.statusMessage.set("Filter By Date.")

    def __bool__(self):
        return self.success

    def createWidgets(self):
        self.title("Filter By Date")

        fromFrame = ttk.Frame(self)
        fromLabel = ttk.Label(fromFrame, text="From", width=8, anchor="e", font=self.parent.defaultFont)
        fromEntry = ttk.Entry(fromFrame, width=30, textvariable=self.fromDateVar)
        fromLabel.pack(side="left", padx=10)
        fromEntry.pack(side="left", fill="x", expand="yes", padx=10)
        fromFrame.pack(side="top", fill="x")

        toFrame = ttk.Frame(self)
        toLabel = ttk.Label(toFrame, text="To", width=8, anchor="e", font=self.parent.defaultFont)
        toEntry = ttk.Entry(toFrame, width=30, textvariable=self.toDateVar)
        toLabel.pack(side="left", padx=10)
        toEntry.pack(side="left", fill="x", expand="yes", padx=10)
        toFrame.pack(side="top", fill="x")

        buttonFrame = ttk.Frame(self)
        buttonFrameInt = ttk.Frame(buttonFrame)
        buttonApply = ttk.Button(buttonFrame, text="Apply", width=12, command=self.applyButtonPressed)
        buttonCancel = ttk.Button(buttonFrame, text="Cancel", width=12, command=self.cancelButtonPressed)
        buttonApply.pack(side="left", padx=10)
        buttonCancel.pack(side="left", padx=10)
        buttonFrameInt.pack(side="top", expand="yes", anchor="c")
        buttonFrame.pack(side="top", padx=10, pady=5)

        statusFrame = ttk.Frame(self)
        statusLabel = ttk.Label(statusFrame, textvariable=self.statusMessage, relief="sunken", width=40)
        statusLabel.pack(side="left", fill="x", expand="yes")
        statusFrame.pack(side="top", fill="x")

    def updateFromAndToDates(self):
        if len(self.app.chat) == 0:
            return
        firstYear, firstMonth, firstDay = self.app.chat.calendar.getFirstDay()
        lastYear, lastMonth, lastDay = self.app.chat.calendar.getLastDay()
        self.fromDateVar.set("{0:04d}-{1:02d}-{2:02d}".format(firstYear, firstMonth, firstDay))
        self.toDateVar.set("{0:04d}-{1:02d}-{2:02d}".format(lastYear, lastMonth, lastDay))

    def getDateFromEntry(self, label, name):
        dateTxt = label.get().strip()
        if len(dateTxt) > 0:
            try:
                date = datetime.datetime.strptime(dateTxt, "%Y-%m-%d").date()
            except:
                self.statusMessage.set("Invalid \"" + name + "\" date, must be yyyy-mm-dd.")
                raise
        else:
            date = None
        return date

    def applyButtonPressed(self):
        try:
            self.fromDate = self.getDateFromEntry(self.fromDateVar, "From")
            self.toDate = self.getDateFromEntry(self.toDateVar, "To")
        except:
            return
        self.success = True
        self.destroy()

    def cancelButtonPressed(self):
        self.success = False
        self.destroy()

    def run(self):
        self.grab_set()
        self.parent.top.wait_window(self)

#
# The UI.
#

class WhatsAppChatBrowser(tkinter.Frame):
    updatePeriodMs = 1000

    def __init__(self, top, useConfigFile=True, configFile=None):
        super().__init__(top)
        self.top = top
        self.app = wacbapp.App(useConfigFile, configFile)
        self.title = tkinter.StringVar()
        self.myName = tkinter.StringVar()
        self.showAs = tkinter.StringVar()
        self.autostart = tkinter.BooleanVar()
        self.emojiImages = tkinter.BooleanVar()
        self.emojiInline = tkinter.BooleanVar()
        self.emojiDataBase = tkinter.StringVar()
        self.emojiPathInZip = tkinter.StringVar()
        self.emojiIgnoreAscii = tkinter.BooleanVar()
        self.builtinCss = tkinter.BooleanVar()
        self.cssFileName = tkinter.StringVar()
        self.inlineImages = tkinter.BooleanVar()
        self.inlineVideo = tkinter.BooleanVar()
        self.inlineAudio = tkinter.BooleanVar()
        self.httpHostName = tkinter.StringVar()
        self.httpPortNumber = tkinter.IntVar()
        self.statusMessage = tkinter.StringVar()
        self.statusMessage.set("WhatsApp Chat Browser.")
        self.statusLoaded = tkinter.StringVar()
        self.statusRunning = tkinter.StringVar()
        self.statisticsCollector = None
        self.widgets = {}
        self.createWidgets()
        self.setupDnd()
        self.updateUiConfigurationFromApp()
        self.updateWidgets()

    def createWidgets(self):
        self.defaultFont = font.Font(family="Times", size=16)
        buttonStyle = ttk.Style()
        buttonStyle.configure("TButton", font=self.defaultFont)
        buttonStyle.configure("TRadiobutton", font=self.defaultFont)

        #
        # Title.
        #

        self.top.title("WhatsApp Chat Browser")

        #
        # Menu bar.
        #

        menuBar = tkinter.Menu()
        fileMenu = tkinter.Menu(menuBar, tearoff=0)
        fileMenu.add_command(label="Open ...", command=self.openFromMenu)
        fileMenu.add_command(label="Merge ...", command=self.mergeFromMenu)
        fileMenu.add_command(label="Close", command=self.closeFromMenu)
        fileMenu.add_separator()
        exportMenu = tkinter.Menu(fileMenu, tearoff=0)
        exportMenu.add_command(label="Chat", command=self.exportChatFromMenu)
        exportMenu.add_command(label="HTML", command=self.exportHtmlFromMenu)
        fileMenu.add_cascade(label="Export", menu=exportMenu)
        fileMenu.add_separator()
        fileMenu.add_command(label="Exit", command=self.exitFromMenu)
        menuBar.add_cascade(label="File", menu=fileMenu)
        self.widgets["fileMenu"] = fileMenu

        filterMenu = tkinter.Menu(menuBar, tearoff=0)
        filterMenu.add_command(label="By Date ...", command=self.filterByDateFromMenu)
        filterMenu.add_separator()
        filterMenu.add_command(label="Reset", command=self.resetFilterFromMenu)
        menuBar.add_cascade(label="Filter", menu=filterMenu)
        self.widgets["filterMenu"] = filterMenu

        serverMenu = tkinter.Menu(menuBar, tearoff=0)
        serverMenu.add_command(label="Start", command=self.startFromMenu)
        serverMenu.add_command(label="Stop", command=self.stopFromMenu)
        serverMenu.add_separator()
        serverMenu.add_command(label="Copy URL to Clipboard", command=self.copyUrlFromMenu)
        serverMenu.add_command(label="Open URL in Browser", command=self.openUrlFromMenu)
        menuBar.add_cascade(label="Server", menu=serverMenu)
        self.widgets["serverMenu"] = serverMenu

        optionsMenu = tkinter.Menu(menuBar, tearoff=0)
        optionsMenu.add_checkbutton(label="Autostart", variable=self.autostart, onvalue=True, offvalue=False)
        htmlMenu = tkinter.Menu(optionsMenu, tearoff=0)
        htmlMenu.add_checkbutton(label="Inline Images", variable=self.inlineImages, onvalue=True, offvalue=False)
        htmlMenu.add_checkbutton(label="Inline Video", variable=self.inlineVideo, onvalue=True, offvalue=False)
        htmlMenu.add_checkbutton(label="Inline Audio", variable=self.inlineAudio, onvalue=True, offvalue=False)
        renderMenu = tkinter.Menu(htmlMenu, tearoff=0)
        renderMenu.add_radiobutton(label="Single Page", variable=self.showAs, value="Single")
        renderMenu.add_radiobutton(label="Annual Pages", variable=self.showAs, value="Annual")
        renderMenu.add_radiobutton(label="Monthly Pages", variable=self.showAs, value="Monthly")
        htmlMenu.add_cascade(label="View As", menu=renderMenu)
        cssMenu = tkinter.Menu(htmlMenu, tearoff=0)
        cssMenu.add_checkbutton(label="Built-In", variable=self.builtinCss, onvalue=True, offvalue=False)
        cssMenu.add_command(label="Load ...", command=self.selectCssFileFromMenu)
        cssMenu.add_command(label="Save Template As ...", command=self.saveCssTemplateFromMenu)
        htmlMenu.add_cascade(label="Style Sheet", menu=cssMenu)
        emojiMenu = tkinter.Menu(htmlMenu, tearoff=0)
        emojiMenu.add_checkbutton(label="Images", variable=self.emojiImages, onvalue=True, offvalue=False)
        emojiMenu.add_checkbutton(label="Inline", variable=self.emojiInline, onvalue=True, offvalue=False)
        emojiMenu.add_checkbutton(label="Ignore Ascii", variable=self.emojiIgnoreAscii, onvalue=True, offvalue=False)
        emojiMenu.add_command(label="Select Images ...", command=self.selectEmojiImagesFromMenu)
        emojiMenu.add_command(label="Download Images ...", command=self.downloadEmojiImagesFromMenu)
        htmlMenu.add_cascade(label="Emojis", menu=emojiMenu)
        optionsMenu.add_cascade(label="HTML", menu=htmlMenu)
        httpMenu = tkinter.Menu(optionsMenu, tearoff=0)
        httpMenu.add_command(label="Configure ...", command=self.configureHTTPFromMenu)
        optionsMenu.add_cascade(label="HTTP", menu=httpMenu)
        menuBar.add_cascade(label="Options", menu=optionsMenu)
        self.widgets["optionsMenu"] = optionsMenu

        self.top.config(menu=menuBar)
        self.top.bind("<Control-o>", self.openFromHotkey)
        self.top.bind("<Control-w>", self.closeFromHotkey)
        self.top.bind("<Control-x>", self.exitFromHotkey)
        self.widgets["menuBar"] = menuBar

        #
        # First frame: File Name / Title.
        #

        titleFrame = ttk.Frame(self.top)
        titleIntFrame = ttk.Frame(titleFrame)
        titleLabel = ttk.Label(titleIntFrame, text="Title", width=10, font=self.defaultFont)
        titleEntry = ttk.Entry(titleIntFrame, width=20, textvariable=self.title)
        titleLabel.pack(side="left")
        titleEntry.pack(side="left", fill="x", expand="yes")
        titleIntFrame.pack(side="top", fill="x")
        titleFrame.pack(side="top", fill="x", padx=10, pady=5)

        #
        # Second frame: My name.
        #

        namesFrame = ttk.Frame(self.top)
        myNameFrame = ttk.Frame(namesFrame)
        myNameLabel = ttk.Label(myNameFrame, text="My Name", width=10, font=self.defaultFont)
        myNameCombo = ttk.Combobox(myNameFrame, width=20, values=[], textvariable=self.myName)
        myNameLabel.pack(side="left")
        myNameCombo.pack(side="left", fill="x", expand="yes")
        myNameFrame.pack(side="top", fill="x")
        namesFrame.pack(side="top", fill="x", padx=10, pady=5)
        self.widgets["myNameCombo"] = myNameCombo

        #
        # Status.
        #

        statusFrame = ttk.Frame(self.top)
        statusLabel = ttk.Label(statusFrame, textvariable=self.statusMessage, relief="sunken", width=40)
        statusLoaded = tkinter.Label(statusFrame, textvariable=self.statusLoaded, relief="sunken", width=12)
        statusRunning = tkinter.Label(statusFrame, textvariable=self.statusRunning, relief="sunken", width=12)
        statusLabel.pack(side="left", fill="x", expand="yes")
        statusLoaded.pack(side="left")
        statusRunning.pack(side="left")
        statusFrame.pack(side="top", fill="x")
        self.widgets["statusLoaded"] = statusLoaded
        self.widgets["statusRunning"] = statusRunning
        statusLoaded.bind("<Button-1>", self.statusLoadedClicked)
        statusRunning.bind("<Button-1>", self.statusRunningClicked)

    @property
    def loaded(self):
        return bool(self.app.chat)

    @property
    def running(self):
        return self.app.running

    #
    # Irritatingly, event.data is a Tcl style list.
    # - File names with spaces are quoted, Tcl-style, with {}.
    # - Multiple file names are separated with spaces.
    #
    
    def filesDropped(self, event=None):
        if event and event.data:
            fileNames = []
            data = event.data
            pos = 0
            while pos < len(data):
                if data[pos] == "{":
                    ep = data.find("}", pos)
                    if ep == -1:
                        return
                    fileNames.append(data[pos+1:ep])
                    pos = ep + 1
                elif data[pos] == " ":
                    pos = pos + 1
                else:
                    ep = data.find(" ", pos)
                    if ep == -1:
                        fileNames.append(data[pos:])
                        pos = len(data)
                    else:
                        fileNames.append(data[pos:ep])
                        pos = ep
            self.open(fileNames)

    def setupDnd(self):
        global haveDnd
        if haveDnd:
            self.top.drop_target_register(tkinterdnd2.DND_FILES)
            self.top.dnd_bind("<<Drop>>", self.filesDropped)

    def updateUiConfigurationFromApp(self):
        config = self.app.config
        if len(config["me"]) > 0:
            self.myName.set(config["me"][0])
        self.autostart.set(config["autostart"])
        self.showAs.set(config["html"]["showAs"])
        self.inlineImages.set(config["html"]["inlineImages"])
        self.inlineVideo.set(config["html"]["inlineVideo"])
        self.inlineAudio.set(config["html"]["inlineAudio"])
        self.builtinCss.set(config["html"]["builtinCss"])
        self.cssFileName.set(config["html"]["cssFileName"])
        self.emojiImages.set(config["emoji"]["images"])
        self.emojiInline.set(config["emoji"]["inline"])
        self.emojiDataBase.set(config["emoji"]["dataBase"])
        self.emojiPathInZip.set(config["emoji"]["pathInZip"])
        self.emojiIgnoreAscii.set(config["emoji"]["ignoreAscii"])
        self.httpHostName.set(config["http"]["hostName"])
        self.httpPortNumber.set(config["http"]["portNumber"])

    def updateAppConfigurationFromUi(self):
        config = self.app.config
        currentMyName = self.widgets["myNameCombo"].get()
        if currentMyName != config["nobody"]:
            config.addMeAlias(currentMyName)
        config["autostart"] = self.autostart.get()
        config["html"]["showAs"] = self.showAs.get()
        config["html"]["builtinCss"] = self.builtinCss.get()
        config["html"]["cssFileName"] = self.cssFileName.get()
        config["html"]["inlineImages"] = self.inlineImages.get()
        config["html"]["inlineVideo"] = self.inlineVideo.get()
        config["html"]["inlineAudio"] = self.inlineAudio.get()
        config["emoji"]["images"] = self.emojiImages.get()
        config["emoji"]["inline"] = self.emojiInline.get()
        config["emoji"]["dataBase"] = self.emojiDataBase.get()
        config["emoji"]["pathInZip"] = self.emojiPathInZip.get()
        config["emoji"]["ignoreAscii"] = self.emojiIgnoreAscii.get()
        config["http"]["hostName"] = self.httpHostName.get()
        config["http"]["portNumber"] = self.httpPortNumber.get()
        self.app.saveConfiguration()

    def updateButtonState(self, name, state):
        stateValue = "!disabled" if state else "disabled"
        self.widgets[name].state([stateValue])

    def updateMenuItemState(self, menu, item, state):
        stateValue = "normal" if state else "disabled"
        self.widgets[menu].entryconfig(item, state=stateValue)

    def updateFileMenuItemState(self, item, state):
        self.updateMenuItemState("fileMenu", item, state)

    def updateFilterMenuItemState(self, item, state):
        self.updateMenuItemState("filterMenu", item, state)

    def updateServerMenuItemState(self, item, state):
        self.updateMenuItemState("serverMenu", item, state)

    def updateMenuBarItemState(self, item, state):
        self.updateMenuItemState("menuBar", item, state)

    def updateWidgets(self):
        global havePyperClip
        self.updateAppConfigurationFromUi()
        self.updateFileMenuItemState("Open ...", not self.running)
        self.updateFileMenuItemState("Merge ...", not self.running)
        self.updateFileMenuItemState("Close", self.loaded)
        self.updateFileMenuItemState("Export", self.loaded)
        self.updateServerMenuItemState("Start", self.loaded and not self.running)
        self.updateServerMenuItemState("Stop", self.running)
        self.updateServerMenuItemState("Copy URL to Clipboard", havePyperClip and self.running)
        self.updateServerMenuItemState("Open URL in Browser", self.running)
        self.updateMenuBarItemState("Filter", self.loaded and not self.running)
        self.updateMenuBarItemState("Options", not self.running)

        loadedBackground = "#00ff00" if self.loaded else self.widgets["statusLoaded"].configure()["background"][3]
        self.widgets["statusLoaded"].configure(background=loadedBackground)
        loadedMessage = "Loaded." if self.loaded else "No file."
        self.statusLoaded.set(loadedMessage)

        runningBackground = "#00ff00" if self.running else self.widgets["statusRunning"].configure()["background"][3]
        self.widgets["statusRunning"].configure(background=runningBackground)
        runningMessage = "Running." if self.running else "Stopped."
        self.statusRunning.set(runningMessage)

    def updateListOfUsersInCombobox(self, userNames, widgetName, configKey):
        widget = self.widgets[widgetName]
        currentName = widget.get()
        widget.configure(values=userNames)
        if currentName not in userNames:
            found = False
            for alias in self.app.config[configKey]:
                if alias in userNames:
                    widget.set(alias)
                    found = True
                    break
            if not found:
                widget.current(0)

    def updateListOfUsers(self):
        userNames = self.app.chat.users.list()
        userNames.sort()
        userNames.insert(0, self.app.config["nobody"])
        self.updateListOfUsersInCombobox(userNames, "myNameCombo", "me")

    def browseForFilesToOpen(self):
        title = "Select chat(s) to open."
        fileTypeSuggestion = [["ZIP Files", "*.zip"], ["TXT Files", "*.txt"]]
        return tkinter.filedialog.askopenfilenames(title=title, filetypes=fileTypeSuggestion)

    def updateWidgetsAfterOpenOrMerge(self):
        self.updateListOfUsers()
        if self.app.chat.groupName:
            self.title.set(self.app.chat.groupName)
        elif isinstance(self.app.fileName, Path):
            self.title.set(self.app.fileName.parts[-1])
        else:
            self.title.set(str(self.app.fileName))
        self.statusMessage.set("{0} messages loaded.".format(len(self.app.chat)))
        self.updateWidgets()
        if self.loaded and self.autostart.get():
            self.start()
        
    def open(self, fileNames):
        try:
            self.app.open(fileNames)
        except:
            self.statusMessage.set("Failed to load \"" + str(fileNames) + "\".")
            return
        self.updateWidgetsAfterOpenOrMerge()

    def merge(self, fileNames):
        try:
            self.app.merge(fileNames)
        except:
            self.statusMessage.set("Failed to load \"" + str(fileNames) + "\".")
            return
        self.updateWidgetsAfterOpenOrMerge()

    def close(self):
        self.app.close()
        self.updateWidgets()
        self.title.set("")
        self.statusMessage.set("No file.")

    def start(self):
        if not self.loaded:
            return
        self.statisticsCollector = DownloadStatisticsCollector()
        self.app.setStatisticsCollector(self.statisticsCollector)
        self.app.title = self.title.get() if len(self.title.get()) > 0 else None
        self.app.start()
        self.updateWidgets()
        self.statusMessage.set("Server started at " + self.app.url + ".")
        self.top.after(WhatsAppChatBrowser.updatePeriodMs, self.updateStatistics)

    def updateStatistics(self):
        if not self.running:
            return
        totalDownloads = self.statisticsCollector.totalDownloads
        activeDownloads = self.statisticsCollector.activeDownloads
        bytesServed = self.statisticsCollector.bytesServed
        if totalDownloads > 0 or bytesServed > 0:
            statsMessage = "{0} downloads, ".format(totalDownloads)
            statsMessage += "{0} active, ".format(activeDownloads)
            statsMessage += "{0:.1f} MB served.".format(bytesServed / (1 << 20))
            self.statusMessage.set(statsMessage)
        self.top.after(WhatsAppChatBrowser.updatePeriodMs, self.updateStatistics)
        
    def stop(self):
        self.app.stop()
        self.updateWidgets()
        self.statusMessage.set("Stopped.")

    def exitFromMenu(self):
        self.app.stop()
        self.app.close()
        self.top.quit()

    def exitFromHotkey(self, event=None):
        self.exitFromMenu()

    def openFromMenu(self):
        fileNames = self.browseForFilesToOpen()
        if len(fileNames) > 0:
            self.open(fileNames)

    def openFromHotkey(self, event=None):
        self.openFromMenu()

    def mergeFromMenu(self):
        fileNames = self.browseForFilesToOpen()
        if len(fileNames) > 0:
            self.merge(fileNames)

    def closeFromMenu(self):
        self.close()
        self.statusMessage.set("No file loaded.")

    def closeFromHotkey(self, event=None):
        self.closeFromMenu()

    def exportChatFromMenu(self):
        defaultExtension = ".zip"
        fileTypeSuggestion = [["ZIP Files", "*.zip"]]
        fileName = tkinter.filedialog.asksaveasfilename(filetypes=fileTypeSuggestion, defaultextension=defaultExtension)
        if fileName == "":
            return
        try:
            self.app.chat.exportToZip(fileName)
        except:
            self.statusMessage.set("Export to \"" + fileName + "\" failed.")
            return
        self.statusMessage.set("Exported chat to \"" + fileName + "\".")

    def exportHtmlFromMenu(self):
        defaultExtension = ".zip"
        fileTypeSuggestion = [["ZIP Files", "*.zip"]]
        fileName = tkinter.filedialog.asksaveasfilename(filetypes=fileTypeSuggestion, defaultextension=defaultExtension)
        if fileName == "":
            return
        try:
            self.app.exportToZip(fileName)
        except:
            self.statusMessage.set("Export to \"" + fileName + "\" failed.")
            return
        self.statusMessage.set("Exported HTML to \"" + fileName + "\".")

    def startFromMenu(self):
        self.start()

    def stopFromMenu(self):
        self.stop()

    def selectEmojiImagesFromMenu(self):
        self.statusMessage.set("Emoji database selection ...")
        emojiSelector = EmojiSelector(self, self.emojiDataBase.get(), self.emojiPathInZip.get())
        emojiSelector.run()
        if emojiSelector:
            self.emojiImages.set(True)
            self.emojiDataBase.set(emojiSelector.fileName.get())
            self.emojiPathInZip.set(emojiSelector.pathInZip.get())
            self.statusMessage.set("Using emoji database \"" + str(self.emojiDataBase.get()) + "\".")
            self.updateAppConfigurationFromUi()
        else:
            self.statusMessage.set("Emoji database selection canceled.")

    def downloadEmojiImagesFromMenu(self):
        self.statusMessage.set("Emoji download ...")
        emojiDownloader = EmojiDownloader(self)
        emojiDownloader.run()
        if emojiDownloader:
            self.emojiImages.set(True)
            self.emojiDataBase.set(emojiDownloader.fileName.get())
            self.emojiPathInZip.set(emojiDownloader.pathInZip.get())
            self.statusMessage.set("Using emoji database \"" + str(self.emojiDataBase.get()) + "\".")
            self.updateAppConfigurationFromUi()
        else:
            self.statusMessage.set("Emoji download canceled.")

    def selectCssFileFromMenu(self):
        self.statusMessage.set("CSS document selection...")
        fileTypeSuggestion = [["CSS Files", "*.css"]]
        fileName = tkinter.filedialog.askopenfilename(filetypes=fileTypeSuggestion)
        if fileName == "":
            return
        self.builtinCss.set(False)
        self.cssFileName.set(str(Path(fileName)))
        self.statusMessage.set("Using CSS document \"" + self.cssFileName.get() + "\".")
        self.updateAppConfigurationFromUi()

    def configureHTTPFromMenu(self):
        httpConfigurator = HttpConfigurator(self, self.httpHostName.get(), self.httpPortNumber.get())
        httpConfigurator.run()
        if httpConfigurator:
            newHostName = httpConfigurator.hostName.get().strip()
            newPortNumber = httpConfigurator.portNumber.get().strip()
            if len(newPortNumber) == 0:
                newPortNumber = "0"
            if (len(newHostName) > 0) and newPortNumber.isdigit():
                self.httpHostName.set(newHostName)
                self.httpPortNumber.set(int(newPortNumber))
                self.updateAppConfigurationFromUi()
                self.statusMessage.set("HTTP Server configuration updated.")
            else:
                self.statusMessage.set("Invalid HTTP Server configuration.")
        else:
            self.statusMessage.set("HTTP Server configuration canceled.")

    def saveCssTemplateFromMenu(self):
        self.statusMessage.set("Saving CSS document template ...")
        defaultExtension = ".css"
        fileTypeSuggestion = [["CSS Files", "*.css"]]
        fileName = tkinter.filedialog.asksaveasfilename(filetypes=fileTypeSuggestion, defaultextension=defaultExtension)
        if fileName == "":
            return
        if not fileName.endswith(".css"):
            fileName += ".css"
        try:
            css = wacbcss.makeBuiltinCss()
            with open(fileName, "w", encoding="utf-8") as cssFile:
                cssFile.write(css.data)
        except:
            self.statusMessage.set("Error writing CSS template to \"" + fileName + "\".")
            return
        self.statusMessage.set("CSS template saved as \"" + fileName + "\".")

    def filterByDateFromMenu(self):
        self.statusMessage.set("Filtering by date ...")
        dateFilter = FilterByDate(self, self.app)
        dateFilter.run()
        if dateFilter:
            self.app.filterByDateRange(dateFilter.fromDate, dateFilter.toDate)
            self.statusMessage.set(str(len(self.app.chat)) + " messages filtered.")
        else:
            self.statusMessage.set("Filter canceled.")

    def resetFilterFromMenu(self):
        if not self.loaded:
            return
        self.app.resetFilter()
        self.statusMessage.set("Filter reset, " + str(len(self.app.chat)) + " messages loaded.")

    def copyUrlFromMenu(self):
        global havePyperClip
        if self.running:
            if havePyperClip:
                pyperclip.copy(self.app.url)
                self.statusMessage.set("Copied \"" + self.app.url + "\" to clipboard.")
            else:
                self.statusMessage.set("Cannot copy to clipboard: Please install \"pyperclip\" module.")

    def openUrlFromMenu(self):
        if self.running:
            webbrowser.open(self.app.url)
            self.statusMessage.set("Opening browser for \"" + self.app.url + "\".")

    def statusLoadedClicked(self, event):
        if self.loaded:
            self.close()
        else:
            self.openFromMenu()

    def statusRunningClicked(self, event):
        if self.running:
            self.stop()
        else:
            self.start()

def run(chatFiles=None, title=None, useConfigFile=True, configFile=None, verbosity=0):
    if haveDnd:
        top = tkinterdnd2.TkinterDnD.Tk()
    else:
        top = tkinter.Tk()
    wacb = WhatsAppChatBrowser(top, useConfigFile, configFile)
    if chatFiles:
        wacb.open(chatFiles)
    if title:
        wacb.title.set(title)
    top.mainloop()

if __name__ == "__main__":
    if __package__ == "wacb":
        from . import wacb
    else:
        import wacb
    wacb.run(True)
