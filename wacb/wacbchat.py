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

import io
import re
import json
import locale
import zipfile
import datetime
from pathlib import Path

#
# Represents a chat user. User names may contain unprintable characters,
# therefore this class also considers the user's "printable" name and allows
# comparing raw and printable names.
#

class User:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.printable)

    def __eq__(self, other):
        if isinstance(other, User):
            return self.name == other.name
        else:
            return self.printable == str(other)

    @property
    def raw(self):
        return self.name

    @property
    def printable(self):
        # - Phone numbers are embedded between \u202a (LRE) and \u202c (PDF).
        #   Remove them.
        # - Phone numbers also use \xa0 (NBSP). Replace them with plain spaces.
        # - Names not from the address book start with "~\u202f" (NNBSP).
        #   Keep the "~" but drop the NNBSP.
        # - Replace multiple whitespace with just one.
        pn = self.name.strip("\u202a\u202c").replace("\u202f", "").replace("\xa0", " ")
        while pn.find("  ") != -1:
            pn = pn.replace("  ", " ")
        return pn

#
# Represents a single message, whether a user message or a system message.
#
# Each message has a timestamp.
# User messages have a user.
# For system messages, the user is None.
# Messages have text, an attachment, or both.
#

class Message:
    def __init__(self, container, index):
        self.container = container
        self.index = index

    @property
    def data(self):
        return self.container.messages[self.index]

    def __str__(self):
        msg = self.time.strftime("[%d.%m.%y, %H:%M:%S]")
        msg += " "
        msg += str(self.user) if self.isUserMessage else "System"
        msg += ": "
        if self.text:
            msg += str(self.text)
        if self.hasAttachment:
            if self.text and len(self.text) > 0:
                msg += " "
            msg += "\u200e<Attached: " + self.attachment + ">"
        return msg

    def __eq__(self, other):
        otherData = other.data if isinstance(other, Message) else other
        return ((self.data[0] == otherData[0]) and
                (self.data[1] == otherData[1]) and
                (self.data[2] == otherData[2]) and
                (self.data[3] == otherData[3]))

    @property
    def time(self):
        return self.data[0]

    @property
    def user(self):
        return User(self.data[1]) if self.data[1] else None

    @property
    def text(self):
        return self.data[2]

    @property
    def attachment(self):
        return self.data[3]

    @property
    def isUserMessage(self):
        return self.user != None

    @property
    def isSystemMessage(self):
        return self.user == None

    @property
    def hasAttachment(self):
        return self.attachment != None

#
# Helper class for calendar, with navigation.
#

class Calendar:
    def __init__(self):
        # A sorted array of years.
        self.years = list()
        # For each year, a sorted array of months.
        self.months = dict()
        # For each year and each month, a sorted array of days.
        self.days = dict()

    def __contains__(self, timestamp):
        year, month, day = timestamp.year, timestamp.month, timestamp.day
        return (year in self.days) and (month in self.days[year]) and (day in self.days[year][month])

    def add(self, timestamp):
        year, month, day = timestamp.year, timestamp.month, timestamp.day

        if year not in self.years:
            self.years.append(year)
            self.years.sort()
            self.months[year] = list()
            self.days[year] = dict()

        if month not in self.months[year]:
            self.months[year].append(month)
            self.months[year].sort()
            self.days[year][month] = list()

        if day not in self.days[year][month]:
            self.days[year][month].append(day)
            self.days[year][month].sort()

    #
    # Get the first and last days.
    #

    @property
    def first(self):
        year, month, day = self.getFirstDay()
        return datetime.date(year, month, day)

    @property
    def last(self):
        year, month, day = self.getLastDay()
        return datetime.date(year, month, day)

    #
    # Get the first and last years, months and days.
    #

    def getFirstYear(self):
        return self.years[0]

    def getLastYear(self):
        return self.years[-1]

    def getFirstMonth(self, year=None):
        firstYear = year if year else self.getFirstYear()
        return firstYear, self.months[firstYear][0]

    def getLastMonth(self, year=None):
        lastYear = year if year else self.getLastYear()
        return lastYear, self.months[lastYear][-1]

    def getFirstDay(self, year=None, month=None):
        firstYear = year if year else self.getFirstYear()
        firstMonth = month if month else self.getFirstMonth(firstYear)[1]
        return firstYear, firstMonth, self.days[firstYear][firstMonth][0]

    def getLastDay(self, year=None, month=None):
        lastYear = year if year else self.getLastYear()
        lastMonth = month if month else self.getLastMonth(lastYear)[1]
        return lastYear, lastMonth, self.days[lastYear][lastMonth][-1]

    #
    # Find the previous available year.
    #

    def getPrevYear(self, year):
        yp = self.years.index(year)
        if yp > 0:
            prevYear = self.years[yp-1]
            return prevYear
        return None

    #
    # Find the previous available month.
    #

    def getPrevMonth(self, year, month):
        mp = self.months[year].index(month)
        if mp > 0:
            prevMonth = self.months[year][mp-1]
            return year, prevMonth
        prevYear = self.getPrevYear(year)
        if prevYear:
            prevMonth = self.months[prevYear][-1]
            return prevYear, prevMonth
        return None, None

    #
    # Find the previous available day.
    #

    def getPrevDay(self, year, month, day):
        dp = self.days[year][month].index(day)
        if dp > 0:
            prevDay = self.days[year][month][dp-1]
            return year, month, prevDay
        prevYear, prevMonth = self.getPrevMonth(year, month)
        if prevMonth:
            prevDay = self.days[prevYear][prevMonth][-1]
            return prevYear, prevMonth, prevDay
        return None, None, None

    #
    # Find the next available year.
    #

    def getNextYear(self, year):
        yp = self.years.index(year)
        if (yp+1) < len(self.years):
            nextYear = self.years[yp+1]
            return nextYear
        return None

    #
    # Find the next available month.
    #

    def getNextMonth(self, year, month):
        mp = self.months[year].index(month)
        if (mp+1) < len(self.months[year]):
            nextMonth = self.months[year][mp+1]
            return year, nextMonth
        nextYear = self.getNextYear(year)
        if nextYear:
            nextMonth = self.months[nextYear][0]
            return nextYear, nextMonth
        return None, None

    #
    # Find the next available day.
    #

    def getNextDay(self, year, month, day):
        dp = self.days[year][month].index(day)
        if (dp+1) < len(self.days[year][month]):
            nextDay = self.days[year][month][dp+1]
            return year, month, nextDay
        nextYear, nextMonth = self.getNextMonth(year, month)
        if nextMonth:
            nextDay = self.days[nextYear][nextMonth][0]
            return nextYear, nextMonth, nextDay
        return None, None, None

#
# Helper list for user list.
#

class UsersList:
    def __init__(self):
        self.users = set()

    def add(self, user):
        if user:
            self.users.add(user)

    def __len__(self):
        return len(self.users)

    def __iter__(self):
        if len(self.users) == 0:
            raise StopIteration
        return UsersIterator(self)

    def find(self, name):
        for user in UsersIterator(self):
            if user == name:
                return user
        return None

    def list(self):
        ul = list()
        for user in UsersIterator(self):
            ul.append(user.printable)
        return ul

#
# Helper class to iterate over users in a user list.
#

class UsersIterator:
    def __init__(self, ul):
        self.ui = ul.users.__iter__()

    def __iter__(self):
        return self

    def __next__(self):
        return User(self.ui.__next__())

#
# Helper class to iterate over messages in a container.
#

class MessageIterator:
    def __init__(self, container):
        self.container = container
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.container.messages):
            raise StopIteration
        this = Message(self.container, self.index)
        self.index += 1
        return this

#
# Container for a chat with many messages.
#

class Chat:
    reForAttachmentsNew = re.compile('\u200e<\\w+: ([ \\w.,-]+)>')
    reForAttachmentsOld = re.compile('([ \\w.,-]+) <\u200e\\w+>')

    def __init__(self):
        self.messages = []
        self.users = UsersList()
        self.calendar = Calendar()
        self.groupName = None
        self.fileName = None
        # In a british locale, we interpret dates as d/m/y instead of m/d/y.
        self.isBritish = "United Kingdom" in str(locale.getlocale(locale.LC_TIME))

    def hasFile(self, name):
        raise Exception("Must be implemented by a derived class.")

    def openFile(self, name):
        raise Exception("Must be implemented by a derived class.")

    def copyFile(self, name, outputFile, updatecb=None):
        raise Exception("Must be implemented by a derived class.")

    def getFileSize(self, name):
        raise Exception("Must be implemented by a derived class.")

    #
    # Return the index of the first message by this user.
    #

    def findByUser(self, user, index=0):
        u = self.users.find(user)
        for i in range(index, len(self.messages)):
            if self.messages[i][1]:
                if u == self.messages[i][1]:
                    return i
        return None

    #
    # Return the index of the first message that has an equal or greater timestamp.
    #

    def findByTimestamp(self, timestamp):
        # This allows the function to accept timestamps of type datetime or date.
        dt = datetime.datetime.combine(timestamp, datetime.time())
        # Binary search, since messages are sorted by time.
        rangeMin = 0
        rangeMax = len(self.messages)
        while rangeMax != rangeMin:
            middleOfRange = (rangeMax + rangeMin) >> 1
            if self.messages[middleOfRange][0] < dt:
                rangeMin = middleOfRange + 1
            else:
                rangeMax = middleOfRange
        return rangeMin

    #
    # To iterate over messages.
    #

    def __bool__(self):
        # Otherwise, objects are considered false if their length is 0.
        return True

    def __len__(self):
        return len(self.messages)

    def __iter__(self):
        return MessageIterator(self)

    #
    # To access messages by index and attachments.
    #

    def __contains__(self, fileNameOrIndex):
        if isinstance(fileNameOrIndex, int):
            if fileNameOrIndex >= 0:
                return fileNameOrIndex < len(self.messages)
            else:
                return len(self.messages) + fileNameOrIndex >= 0
        elif isinstance(fileNameOrIndex, str):
            return self.hasFile(fileNameOrIndex)
        else:
            raise TypeError

    def __getitem__(self, fileNameOrIndex):
        if isinstance(fileNameOrIndex, int):
            if (fileNameOrIndex >= 0) and (fileNameOrIndex < len(self.messages)):
                return Message(self, fileNameOrIndex)
            elif (fileNameOrIndex < 0) and (len(self.messages) + fileNameOrIndex >= 0):
                return Message(self, len(self.messages) + fileNameOrIndex)
            raise IndexError
        elif isinstance(fileNameOrIndex, str):
            if not self.hasFile(fileNameOrIndex):
                raise KeyError
            with self.openFile(fileNameOrIndex) as file:
                return file.read()
        else:
            raise TypeError

    def parseDate(self, strDate):
        #
        # If the date has dots, assume d.m.y.
        # If the date has slashes, assume m/d/y, unless our locale is british.
        #
        
        if "." in strDate:
            day, month, year = [int(v) for v in strDate.split(".")]
        elif "/" in strDate:
            if self.isBritish:
                day, month, year = [int(v) for v in strDate.split("/")]
            else:
                month, day, year = [int(v) for v in strDate.split("/")]
        else:
            raise Exception("Unrecognized date format \"" + strDate + "\".")

        if year < 100:
            year += 2000

        return datetime.date(year, month, day)

    def parseTime(self, strTime):
        #
        # The time is h:m:s, and may be followed by \u202f (NNBSP) and "AM" or "PM".
        #

        nnbspPos = strTime.find("\u202f")

        if nnbspPos == -1:
            hour, minute, second = [int(v) for v in strTime.split(":")]
        else:
            hour, minute, second = [int(v) for v in strTime[:nnbspPos].split(":")]
            if strTime[nnbspPos+1] == 'P':
                hour += 12

        return datetime.time(hour, minute, second)

    def parseTimestamp(self, strDateTime):
        #
        # The timestamp has date and time separated by comma.
        #
        # Both date and time are localized according to the locale of
        # WhatsApp at the time of export.
        #

        commaPos = strDateTime.find(", ")
        date = self.parseDate(strDateTime[:commaPos])
        time = self.parseTime(strDateTime[commaPos+2:])
        return datetime.datetime.combine(date, time)
        
    def parseAttachment(self, message):
        #
        # In newer WhatsApp versions, attachments are embedded in user messages like
        #     '_text_ \u200e<Attached: _filename_>'
        # The "Attached" keyword is localized.
        #

        m = Chat.reForAttachmentsNew.search(message)

        if m and self.hasFile(m[1]):
            endOfPlainText = m.start(0)
            messageText = message[0:endOfPlainText].strip()
            if len(messageText) == 0:
                messageText = None
            return messageText, m[1]

        #
        # In older WhatsApp versions, attachments are embedded in user messages like
        #     '_file_ <\u200eattached>'
        # The "attached" keyword is again localized. These messages do not contain
        # any other text.
        #

        m = Chat.reForAttachmentsOld.search(message)

        if m and self.hasFile(m[1]):
            return None, m[1]

        #
        # This message does not appear to have an attachment.
        #

        return message, None

    def parseMessage(self, txtLine):
        #
        # Sometimes, lines start with \u200e. I don't know if there is meaning
        # to it. If it is there, ignore it.
        #

        startPos = 1 if txtLine[0] == '\u200e' else 0

        #
        # Each line starts with a timestamp. Earlier versions had a timestamp
        # followed by a colon, later versions have a timestamp in brackets.
        #

        if txtLine[startPos] == '[':
            endPos = txtLine.find('] ')
            strDateTime = txtLine[startPos+1:endPos]
        else:
            endPos = txtLine.find(': ')
            strDateTime = txtLine[startPos:endPos]

        userNamePos = endPos + 2
        timestamp = self.parseTimestamp(strDateTime)

        #
        # After the timestamp, there is the user name, except, in earlier
        # versions, for system messages.
        #

        userNameEnd = txtLine.find(": ", userNamePos)

        if userNameEnd == -1:
            userName = None
            messageText = txtLine[userNamePos:].strip()
        else:
            userName = txtLine[userNamePos:userNameEnd].strip()
            messageText = txtLine[userNameEnd+2:].strip()

        #
        # When the message text starts with \u200e ("left-to-right-mark"),
        # then this is a system message, and the user name field may be an
        # indication of the group's name.
        #

        startsWithLTM = (messageText[0] == '\u200e') if len(messageText)>0 else False

        if startsWithLTM and len(messageText) > 1 and messageText[1] != '<':
            if not self.groupName:
                self.groupName = userName
            userName = None

        if not userName:
            # System message.
            userName = None
            attachment = None
            text = messageText
        else:
            text, attachment = self.parseAttachment(messageText)

        return (timestamp, userName, text, attachment)

    def addMessage(self, message):
        self.messages.append(message)
        self.calendar.add(message[0])
        self.users.add(message[1])

    def parseAndAddMessage(self, txtLine):
        if len(txtLine) == 0:
            return
        message = self.parseMessage(txtLine)
        self.addMessage(message)

    def loadMessagesFromStream(self, stream):
        data = stream.read()
        rawLines = data.split(b'\r\n')
        for rawLine in rawLines:
            txtLine = rawLine.decode()
            self.parseAndAddMessage(txtLine)

    #
    # Export messages to a binary stream.
    #
    
    def exportMessages(self, stream):
        for message in self:
            stream.write(str(message).encode())
            stream.write(b'\r\n')
            
    #
    # Export a chat to a Zip file.
    #
    # Useful, e.g., after filtering and/or merging.
    #
    # All files are stored without compression. Images and videos are compressed
    # formats anyway, so additional compression doesn't do much. The _chat.txt
    # file is more compressible, but since it's tiny compared to any attachments,
    # we don't bother.
    #
    # Note that fileName can also be a file-like object.
    #

    def exportToZip(self, fileName):
        with zipfile.ZipFile(fileName, "w") as zFile:
            for message in self:
                if message.hasAttachment:
                    with zFile.open(message.attachment, 'w') as aFile:
                        self.copyFile(message.attachment, aFile)
            with zFile.open("_chat.txt", 'w') as cFile:
                self.exportMessages(cFile)

#
# Archives export from WhatsApp are ZIP files.
# The ZIP file contains the file "_chat.txt".
# This is a text file in UTF-8 format where each line is a message.
# Note hat ZipFile also accepts file-like objects.
#

class ZippedChat(Chat):
    def findPaths(fileName):
        paths = []
        with zipfile.ZipFile(fileName) as zipFile:
            for name in zipFile.namelist():
                if name.endswith("_chat.txt"):
                    paths.append(name[:-9])
        return paths

    def __init__(self, fileName, pathInZip=None):
        super().__init__()
        if isinstance(fileName, str) or isinstance(fileName, Path):
            self.fileName = Path(fileName)
        else:
            self.fileName = None
        self.zipFile = None
        self.zipFile = zipfile.ZipFile(fileName)
        self.attachments = self.zipFile.namelist()
        self.pathInZip = pathInZip if pathInZip else self.findPath()
        self.loadMessages()

    def __del__(self):
        if self.zipFile != None:
            self.zipFile.close()
            self.zipFile = None

    def findPath(self):
        for name in self.zipFile.namelist():
            if name.endswith("_chat.txt"):
                return name[:-9]
        raise Exception("ZIP file \"" + str(self.fileName) + "\" has no file \"_chat.txt\"")

    def canonicalName(self, name):
        fileName = name if ((len(name) < 2) or (name[0] != "/")) else name[1:]
        return self.pathInZip + fileName

    def hasFile(self, name):
        return self.canonicalName(name) in self.attachments

    def openFile(self, name):
        return self.zipFile.open(self.canonicalName(name))

    #
    # Copying data in slices seems to deadlock sometimes. A workaround
    # is to read the file into memory at once, and then to write the data
    # to the output file in slices.
    #

    def copyFile(self, name, outputFile, updatecb=None):
        data = self.zipFile.read(self.canonicalName(name))
        pos = 0
        sliceSize = 16384
        while pos < len(data):
            slice = data[pos:pos+sliceSize]
            outputFile.write(slice)
            pos += len(slice)
            if updatecb:
                updatecb.update(len(slice))

    def getFileSize(self, name):
        return self.zipFile.getinfo(self.canonicalName(name)).file_size

    def loadMessages(self):
        with self.zipFile.open(self.canonicalName("_chat.txt")) as file:
            self.loadMessagesFromStream(file)

#
# Load a "_chat.txt" text file. Look for attachments in the same directory.
#

class TextChat(Chat):
    def __init__(self, fileName):
        super().__init__()
        if isinstance(fileName, str) or isinstance(fileName, Path):
            self.fileName = Path(fileName)
            self.dir = self.fileName.parent
            self.attachments = [str(f.name) for f in self.dir.iterdir()]
            self.loadMessages(fileName)
        elif isinstance(fileName, io.TextIOBase):
            self.fileName = None
            self.dir = None
            self.attachments = list()
            self.loadMessagesFromStream(fileName)
        else:
            raise TypeError

    def canonicalName(name):
        return name if ((len(name) < 2) or (name[0] != "/")) else name[1:]

    def hasFile(self, name):
        return TextChat.canonicalName(name) in self.attachments

    def openFile(self, name):
        return open(self.dir / TextChat.canonicalName(name), "rb")

    def copyFile(self, name, outputFile, updatecb=None):
        pos = 0
        sliceSize = 16384
        with self.openFile(name) as inputFile:
            while True:
                slice = inputFile.read(sliceSize)
                if len(slice) == 0:
                    break
                outputFile.write(slice)
                if updatecb:
                    updatecb.update(len(slice))

    def getFileSize(self, name):
        fp = self.dir / TextChat.canonicalName(name)
        return fp.stat().st_size

    def loadMessages(self, fileName):
        with open(fileName, "rb") as file:
            self.loadMessagesFromStream(file)

#
# Load a chat from a JSON file as exported by WhatsApp-Chat-Exporter.
#

class JsonChat(Chat):
    def __init__(self, fileName, chatId=None):
        super().__init__()
        if isinstance(fileName, str) or isinstance(fileName, Path):
            self.fileName = Path(fileName)
            self.dir = self.fileName.parent
            self.attachments = dict()
            self.loadJsonMessagesFromFile(fileName, chatId)
        elif isinstance(fileName, io.TextIOBase):
            self.fileName = None
            self.dir = None
            self.attachments = dict()
            self.loadJsonMessagesFromStream(fileName, chatId)
        elif not fileName:
            self.fileName = None
            self.dir = None
            self.attachments = dict()
        else:
            raise TypeError

    def canonicalName(name):
        return name if ((len(name) < 2) or (name[0] != "/")) else name[1:]

    def hasFile(self, name):
        return JsonChat.canonicalName(name) in self.attachments

    def openFile(self, name):
        return open(self.attachments[JsonChat.canonicalName(name)], "rb")

    def copyFile(self, name, outputFile, updatecb=None):
        pos = 0
        sliceSize = 16384
        with self.openFile(name) as inputFile:
            while True:
                slice = inputFile.read(sliceSize)
                if len(slice) == 0:
                    break
                outputFile.write(slice)
                if updatecb:
                    updatecb.update(len(slice))

    def getFileSize(self, name):
        return self.attachments[JsonChat.canonicalName(name)].stat().st_size

    def loadJsonMessagesFromFile(self, fileName, chatId=None):
        with open(fileName, "rb") as file:
            self.loadJsonMessagesFromStream(file, chatId)

    def loadJsonMessagesFromStream(self, file, chatId=None):
        jsonData = json.load(file)
        self.loadJsonMessagesFromJson(jsonData)

    def loadJsonMessagesFromJson(self, jsonData, chatId=None):
        if not chatId:
            chatId = list(jsonData.keys())[0]
        chat = jsonData[chatId]
        messages = chat["messages"]
        self.groupName = chat["name"]
        self.mediaBase = self.dir / chat["media_base"] if chat["media_base"] else None
        for messageId in messages.keys():
            self.parseAndAddJsonMessage(messages[messageId])

    def parseAndAddJsonMessage(self, jsonMessage):
        timestamp = datetime.datetime.fromtimestamp(jsonMessage["timestamp"])

        if jsonMessage["from_me"]:
            userName = "Me"
        elif jsonMessage["meta"]:
            userName = None
        elif jsonMessage["sender"]:
            userName = jsonMessage["sender"]
        else:
            userName = self.groupName

        if jsonMessage["media"] and self.isAttachmentAvailable(jsonMessage["data"]):
            text = jsonMessage["caption"]
            attachment = self.importAttachment(jsonMessage["data"])
        elif jsonMessage["data"]:
            text = jsonMessage["data"].replace("<br>", "\n")
            attachment = None
        else:
            # No text, no media - ignore.
            return

        self.addMessage((timestamp, userName, text, attachment))

    def isAttachmentAvailable(self, attachmentName):
        if not self.mediaBase:
            return False
        attachmentPath = Path(attachmentName)
        fullPath = self.mediaBase / attachmentPath
        return fullPath.is_file()
        
    def importAttachment(self, attachmentName):
        attachmentPath = Path(attachmentName)
        fullPath = self.mediaBase / attachmentPath
        nn = "{0:08d}-{1}".format(len(self.messages), attachmentPath.name)
        self.attachments[nn] = fullPath
        return nn

#
# Container for an empty chat.
#

class NullChat(Chat):
    pass

#
# Filter messages by time.
#
# We simply iterate over all messages in a chat and import the ones
# within the desired range.
#

class FilteredByTime(Chat):
    def __init__(self, otherChat, fromTimestamp=None, toTimestamp=None):
        super().__init__()
        self.fileName = otherChat.fileName
        self.otherChat = otherChat
        self.fromDate = fromTimestamp
        self.toTDate = toTimestamp
        self.importMessages(fromTimestamp, toTimestamp)

    def hasFile(self, name):
        return self.otherChat.hasFile(name)

    def openFile(self, name):
        return self.otherChat.openFile(name)

    def copyFile(self, name, outputFile, updatecb):
        return self.otherChat.copyFile(name, outputFile, updatecb)

    def getFileSize(self, name):
        return self.otherChat.getFileSize(name)

    def importMessages(self, fromTimestamp, toTimestamp):
        if fromTimestamp:
            startIndex = self.otherChat.findByTimestamp(fromTimestamp)
        else:
            startIndex = 0

        if isinstance(toTimestamp, datetime.date):
            toTimestamp += datetime.timedelta(days=1)
            toTimestamp = datetime.datetime.combine(toTimestamp, datetime.time())
        elif isinstance(toTimestamp, datetime.datetime):
            toTimestamp += datetime.timedelta(seconds=1)

        for i in range(startIndex, len(self.otherChat)):
            message = self.otherChat[i]

            if toTimestamp and message.time > toTimestamp:
                break

            self.addMessage(message.data)

#
# Merge multiple chats into one timeline.
#

class MergedChat(Chat):
    # Takes a list of Chat.
    def __init__(self, chats):
        super().__init__()
        self.chats = chats
        self.attachments = dict()
        self.importMessages()
        if len(self.chats) == 0:
            self.fileName = None
        elif len(self.chats) == 1:
            self.fileName = self.chats[0].fileName
        else:
            self.fileName = "(Merged)"

    def canonicalName(name):
        return name if ((len(name) < 2) or (name[0] != "/")) else name[1:]

    def hasFile(self, name):
        return MergedChat.canonicalName(name) in self.attachments

    def openFile(self, name):
        attachment = self.attachments[MergedChat.canonicalName(name)]
        return self.chats[attachment[0]].openFile(attachment[1])

    def copyFile(self, name, outputFile, updatecb=None):
        attachment = self.attachments[MergedChat.canonicalName(name)]
        return self.chats[attachment[0]].copyFile(attachment[1], outputFile, updatecb)

    def getFileSize(self, name):
        attachment = self.attachments[MergedChat.canonicalName(name)]
        return self.chats[attachment[0]].getFileSize(attachment[1])

    def importMessage(self, message, index):
        messageData = list(message.data)
        if message.hasAttachment:
            # Attachment filenames begin with a sequence number.
            # We drop that sequence number and use our own.
            on = message.attachment
            dp = on.find("-")
            fn = on[dp+1:] if dp != -1 and on[:dp].isdigit() else on
            nn = "{0:08d}-{1}".format(len(self.messages), fn)
            self.attachments[nn] = (index, on)
            messageData[3] = nn
        if len(self) == 0 or self[-1] != messageData:
            self.addMessage(messageData)

    # Iterate over all messages in all chats, and import them, always
    # selecting the message with the lowest timestamp next.
    def importMessages(self):
        indices = [0] * len(self.chats)
        nextIndex = self.getIndexOfNextMessage(indices)
        while nextIndex != None:
            message = self.chats[nextIndex][indices[nextIndex]]
            self.importMessage(message, nextIndex)
            indices[nextIndex] += 1
            nextIndex = self.getIndexOfNextMessage(indices)

    # Find the next message, i.e., the one with the lowest timestamp.
    # indices is an array of index values, one for each of the chats.
    def getIndexOfNextMessage(self, indices):
        lowestIndex = None
        lowestTimestamp = None
        for i in range(len(self.chats)):
            if indices[i] < len(self.chats[i]):
                thisTimestamp = self.chats[i][indices[i]].time
                if (lowestTimestamp == None) or (thisTimestamp < lowestTimestamp):
                    lowestIndex = i
                    lowestTimestamp = thisTimestamp
        return lowestIndex

#
# Generic, flexible open function.
#

def openChat(files):
    if isinstance(files, list) or isinstance(files, tuple):
        if len(files) == 0:
            return NullChat()
        elif len(files) == 1:
            return openChat(files[0])
        else:
            return MergedChat([openChat(file) for file in files])

    file = files
    if isinstance(file, io.TextIOBase):
        file.seek(0)
        first8Chars = file.read(8)
        file.seek(0)
        if len(first8Chars) > 0 and first8Chars[0] == '{':
            return JsonChat(file)
        else:
            return TextChat(file)
    elif zipfile.is_zipfile(file):
        paths = ZippedChat.findPaths(file)
        if len(paths) <= 1:
            return ZippedChat(file)
        else:
            return MergedChat([ZippedChat(file, path) for path in paths])
    elif isinstance(file, str) or isinstance(file, Path):
        path = Path(file)
        if path.suffix == ".zip":
            return ZippedChat(path)
        elif path.suffix == ".txt":
            return TextChat(path)
        elif path.suffix == ".json":
            return JsonChat(path)
        elif path.is_dir():
            textFile = path / "_chat.txt"
            if textFile.exists():
                return TextChat(textFile)
    raise TypeError

#
# For testing and debugging: Get an array of lines from the chat.
#

def getRawLines(fn):
    with zipfile.ZipFile(fn) as zipFile:
        with zipFile.open("_chat.txt") as txtFile:
            rawlines = txtFile.read().split(b'\r\n')
    return [rawline.decode() for rawline in rawlines]

#
# Allow merging chats from the command line.
#

def mergeChats(outputFile, chatFiles, verbose):
    chats = []
    for fn in chatFiles:
        if verbose:
            print("Loading \"" + fn + "\" ... ", end="", flush=True)
        chat = openChat(fn)
        if verbose:
            print("{0} messages loaded.".format(len(chat)))
        chats.append(chat)
        
    if verbose:
        print("Merging \"" + fn + "\" ... ", end="", flush=True)
    mergedChat = MergedChat(chats)
    if verbose:
        print("{0} messages merged.".format(len(mergedChat)))

    if verbose:
        print("Exporting \"" + fn + "\" ... ", end="", flush=True)
    mergedChat.exportToZip(outputFile)
    if verbose:
        print("done.")

def mergeChatsCli():
    import argparse
    import glob
    parser = argparse.ArgumentParser(prog="WhatsApp Chat Merger")
    parser.add_argument('--outputFile', default=None, help="Tie Zip file to write the merged chat to.")
    parser.add_argument('-v', '--verbose', default=False, action=argparse.BooleanOptionalAction, help="Print information about progress.")
    parser.add_argument('chats', nargs="+", default=[], help="Chats to import.")
    args = parser.parse_args()
    chatFiles = []
    for chat in args.chats:
        chatFiles.extend(glob.glob(chat))
    mergeChats(args.outputFile, chatFiles, args.verbose)

if __name__ == "__main__":
    mergeChatsCli()
