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
Classes and functions for loading and processing chats.
"""

import io
import re
import json
import locale
import zipfile
import datetime
import pathlib

class User:
    """
    Represents a chat user. User names may contain unprintable characters,
    therefore this class also considers the user's "printable" name and allows
    comparing raw and printable names.
    """

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

class Message:
    """
    Represents a single message, whether a user message or a system message.

    Each message has a timestamp.
    User messages have a user.
    For system messages, the user is None.
    Messages have text, an attachment, or both.
    """

    def __init__(self, data):
        self.data = data

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
            msg += "\u200e<Attached: " + str(self.attachment) + ">"
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
        return self.user is not None

    @property
    def isSystemMessage(self):
        return self.user is None

    @property
    def hasAttachment(self):
        return self.attachment is not None

class Attachment:
    """
    Represents an attachment.

    An attachment references a file system and a path within the file system.
    Attachments also have a flat name. E.g., the path can be "a/b/c.jpg", but
    the name is "c.jpg".

    It is assumed that attachment names are unique within a chat.
    """

    def __init__(self, fs, path, name=None):
        self.fs = fs
        self.path = path
        self.name = str(name) if name else str(path)

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name

    def openFile(self):
        return self.fs.openFile(self.path)

    def copyFile(self, outputFile, updatecb=None):
        return self.fs.copyFile(self.path, outputFile, updatecb)

    def getFileSize(self):
        return self.fs.getFileSize(self.path)

class Calendar:
    """
    Helper class for a calendar, with navigation.

    This calendar collects all dates for which messages are available.
    I.e., it is not a general-purpose wall calendar, but it only has
    entries for which at least one message is available.

    E.g., "getNextDay" returns the next day for which there is a
    chat message. If there are messages on Jan 17 and Feb 12,
    getNextDay(Jan 17) would not return Jan 18, but Feb 12.
    """

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

class UsersList:
    """
    Helper list for user list.
    """

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

class UsersIterator:
    """
    Helper class to iterate over users in a user list.
    """

    def __init__(self, ul):
        self.ui = ul.users.__iter__()

    def __iter__(self):
        return self

    def __next__(self):
        return User(self.ui.__next__())

class MessageIterator:
    """
    Helper class to iterate over messages in a container.
    """

    def __init__(self, container):
        self.container = container
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.container.messages):
            raise StopIteration
        this = self.container[self.index]
        self.index += 1
        return this

class Vfs:
    """
    Helper pure virtual file-system class.
    """

    def __init__(self):
        pass

    def findAllChats(self):
        return list()

    def hasFile(self, name):
        raise Exception("Must be implemented by a derived class.")

    def openFile(self, name):
        raise Exception("Must be implemented by a derived class.")

    def copyFile(self, name, outputFile, updatecb=None):
        raise Exception("Must be implemented by a derived class.")

    def getFileSize(self, name):
        raise Exception("Must be implemented by a derived class.")

class FileFs(Vfs):
    """
    Helper class for using file I/O for chats and attachments.
    """

    def __init__(self, basePath):
        super().__init__()
        self.basePath = None
        self.setPath(basePath)

    def setPath(self, basePath):
        self.basePath = pathlib.Path(basePath)
        if self.basePath.is_file():
            self.basePath = self.basePath.parent
        if not self.basePath.is_dir():
            raise Exception("\"" + str(basePath) + "\" is not a directory.")

    def findAllChats(self):
        paths = list()
        for file in self.basePath.iterdir():
            name = file.name
            if name == "_chat.txt" or name.suffix == ".json":
                paths.append(name)
        return paths

    def canonicalName(self, name):
        fileName = name if ((len(name) < 2) or (name[0] != "/")) else name[1:]
        filePath = self.basePath / fileName
        return filePath

    def hasFile(self, name):
        return self.canonicalName(name).is_file()

    def openFile(self, name):
        return open(self.canonicalName(name), "rb")

    def copyFile(self, name, outputFile, updatecb=None):
        sliceSize = 16384
        with self.openFile(name) as inputFile:
            while True:
                sliceData = inputFile.read(sliceSize)
                if len(sliceData) == 0:
                    break
                outputFile.write(sliceData)
                if updatecb:
                    updatecb.update(len(sliceData))

    def getFileSize(self, name):
        return self.canonicalName(name).stat().st_size

class ZipFs(Vfs):
    """
    Helper class for reading chats and attachments from Zip files.
    """

    def __init__(self, fileName, pathInZip=None):
        # pylint: disable=consider-using-with
        super().__init__()
        self.zipFile = None
        self.zipFile = zipfile.ZipFile(fileName)
        self.namelist = self.zipFile.namelist()
        self.pathInZip = None
        self.setPath(pathInZip)

    def __del__(self):
        if self.zipFile is not None:
            self.zipFile.close()
            self.zipFile = None

    def setPath(self, pathInZip):
        self.pathInZip = pathlib.PurePath(pathInZip) if pathInZip else None

    def findAllChats(self):
        paths = list()
        for name in self.namelist:
            if name.endswith("_chat.txt") or name.endswith(".json"):
                paths.append(name)
        return paths

    def canonicalName(self, name):
        fileName = name if ((len(name) < 2) or (name[0] != "/")) else name[1:]
        if self.pathInZip:
            filePath = self.pathInZip / fileName
            return filePath.as_posix()
        else:
            return fileName

    def hasFile(self, name):
        return self.canonicalName(name) in self.namelist

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
            sliceData = data[pos:pos+sliceSize]
            outputFile.write(sliceData)
            pos += len(sliceData)
            if updatecb:
                updatecb.update(len(sliceData))

    def getFileSize(self, name):
        return self.zipFile.getinfo(self.canonicalName(name)).file_size

class Chat:
    """
    Container for a chat with many messages and attachments.
    """

    def __init__(self, fs=None):
        self.messages = list()
        self.users = UsersList()
        self.calendar = Calendar()
        self.attachments = dict()
        self.groupName = None
        self.fileName = None
        self.fs = fs

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

    def findByTimestamp(self, dt):
        # This allows the function to accept timestamps of type datetime or date.
        if isinstance(dt, datetime.datetime):
            pass
        elif isinstance(dt, datetime.date):
            dt = datetime.datetime.combine(dt, datetime.time())
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
    # To access messages by index.
    #

    def __contains__(self, index):
        if index >= 0:
            return index < len(self.messages)
        else:
            return len(self.messages) + index >= 0

    def __getitem__(self, index):
        if (index >= 0) and (index < len(self.messages)):
            return Message(self.messages[index])
        elif (index < 0) and (len(self.messages) + index >= 0):
            return Message(self.messages[len(self.messages) + index])
        raise IndexError

    #
    # To access attachments by name.
    #

    def canonicalName(self, name):
        return name if ((len(name) < 2) or (name[0] != "/")) else name[1:]

    def hasFile(self, name):
        return self.canonicalName(name) in self.attachments

    def openFile(self, name):
        attachment = self.attachments[self.canonicalName(name)]
        return attachment.openFile()

    def copyFile(self, name, outputFile, updatecb=None):
        attachment = self.attachments[self.canonicalName(name)]
        return attachment.copyFile(outputFile, updatecb)

    def getFileSize(self, name):
        attachment = self.attachments[self.canonicalName(name)]
        return attachment.getFileSize()

    #
    # Make a flat, unique file name for attachments. This applies to chats
    # that are not using "_chat.txt" format. WhatsApp Chat Exporter-exported
    # chats and Telegram chats have attachments in subdirectories, and for
    # merged chats, we need to ensure unique names.
    #
    # Other logic elsewhere, e.g., for HTTP requests or for exporting chats,
    # depends on flat names.
    #

    def makeSimpleNameForAttachment(self, attachmentPath):
        flatName = pathlib.PurePath(attachmentPath).name
        # If the filename begins with a sequence number, replace it.
        dashPos = flatName.find("-")
        remainder = flatName[dashPos+1:] if dashPos != -1 and flatName[:dashPos].isdigit() else flatName
        simpleName = "{0:08d}-{1}".format(len(self.messages), remainder)
        simpleName = simpleName.replace("@", "-").replace("(", "_").replace(")", "_")
        return simpleName

    #
    # Add a message to this chat. The message should be a tuple:
    #
    # - message[0]: message timestamp, as a datetime object.
    # - message[1]: user name as a str, or None for system messages.
    # - message[2]: message text as a str, or None.
    # - message[3]: an Attachment object.
    #
    # This function is typically called from derived classes only.
    #

    def addMessage(self, message):
        if isinstance(message, Message):
            message = message.data
        if len(message) != 4:
            raise TypeError
        if not isinstance(message[0], datetime.datetime):
            raise TypeError
        if message[3]:
            if not isinstance(message[3], Attachment):
                raise TypeError
            self.attachments[message[3].name] = message[3]
        self.messages.append(message)
        self.calendar.add(message[0])
        self.users.add(message[1])

    #
    # Export messages to a binary stream, in "_chat.txt" format.
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
                    with zFile.open(str(message.attachment), 'w') as aFile:
                        message.attachment.copyFile(aFile)
            with zFile.open("_chat.txt", 'w') as cFile:
                self.exportMessages(cFile)

class WaChat(Chat):
    """
    A chat using WhatsApp's _chat.txt file format, a text file in UTF-8
    format where each line is a message.
    """

    reForAttachmentsNew = re.compile('\u200e<\\w+: ([ \\w.,-]+)>')
    reForAttachmentsOld = re.compile('([ \\w.,-]+) <\u200e\\w+>')

    def __init__(self, fs=None):
        super().__init__(fs)
        # In a british locale, we interpret dates as d/m/y instead of m/d/y.
        # This requires that locale.setlocale(locale.LC_ALL, '') was called first.
        self.isBritish = "United Kingdom" in str(locale.getlocale(locale.LC_TIME))

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

        #
        # If the year was two digits, assume that it's this millenium.
        #

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

        m = WaChat.reForAttachmentsNew.search(message)

        if m and self.fs and self.fs.hasFile(m[1]):
            endOfPlainText = m.start(0)
            messageText = message[0:endOfPlainText].strip()
            if len(messageText) == 0:
                messageText = None
            return messageText, Attachment(self.fs, m[1])

        #
        # In older WhatsApp versions, attachments are embedded in user messages like
        #     '_file_ <\u200eattached>'
        # The "attached" keyword is again localized. These messages do not contain
        # any other text.
        #

        m = WaChat.reForAttachmentsOld.search(message)

        if m and self.fs and self.fs.hasFile(m[1]):
            return None, Attachment(self.fs, m[1])

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

    def loadMessagesFromFile(self, fileName):
        with self.fs.openFile(fileName) as stream:
            self.loadMessagesFromStream(stream)

class WaceJsonChat(Chat):
    """
    Load a chat from a JSON file as exported by WhatsApp-Chat-Exporter.
    """

    @staticmethod
    def isWaceJson(jsonData):
        if isinstance(jsonData, dict):
            firstId = list(jsonData.keys())[0]
            if firstId != "chats":
                if isinstance(jsonData[firstId], dict):
                    return "messages" in jsonData[firstId]
        return False

    def __init__(self, fs=None):
        super().__init__(fs)
        self.mediaBase = pathlib.PurePath()

    def loadMessagesFromFile(self, fileName, chatId=None):
        if chatId is None and isinstance(fileName, str) and fileName.find("#") != -1:
            fileName, chatId = fileName.split("#")
        with self.fs.openFile(fileName) as stream:
            self.loadMessagesFromStream(stream, chatId, fileName)

    def loadMessagesFromStream(self, file, fileName=None, chatId=None):
        jsonData = json.load(file)
        self.loadMessagesFromJson(jsonData, fileName, chatId)

    def loadMessagesFromJson(self, jsonData, fileName=None, chatId=None):
        self.fileName = fileName
        if not chatId:
            chatId = list(jsonData.keys())[0]
        if not chatId in jsonData:
            raise Exception("Chat \"" + chatId + "\" not found in archive.")
        chat = jsonData[chatId]
        messages = chat["messages"]
        self.groupName = chat["name"]
        self.mediaBase = pathlib.PurePath(chat["media_base"] if chat["media_base"] else "")
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
        if not self.fs:
            return False
        attachmentFqd = self.mediaBase / attachmentName
        attachmentPath = attachmentFqd.as_posix()
        print("isAttachmentAvailable: " + str(attachmentPath) + "= " + str(self.fs.hasFile(attachmentPath)))
        return self.fs.hasFile(attachmentPath)

    def importAttachment(self, attachmentName):
        attachmentFqd = self.mediaBase / attachmentName
        attachmentPath = attachmentFqd.as_posix()
        simpleName = self.makeSimpleNameForAttachment(attachmentFqd)
        return Attachment(self.fs, attachmentPath, simpleName)

class TelegramJsonChat(Chat):
    """
    Load a chat from a JSON file as exported by Telegram Desktop.
    """

    def __init__(self, fs=None):
        # pylint: disable=useless-parent-delegation
        super().__init__(fs)

    def loadMessagesFromFile(self, fileName):
        with self.fs.openFile(fileName) as stream:
            self.loadMessagesFromStream(stream, fileName)

    def loadMessagesFromStream(self, file, fileName=None):
        chatData = json.load(file)
        self.loadMessagesFromJson(chatData, fileName)

    def loadMessagesFromJson(self, chatData, fileName=None, chatId=None):
        raise Exception("Must be implemented by a derived class.")

    def parseAndAddJsonMessage(self, jsonMessage):
        timestamp = datetime.datetime.fromisoformat(jsonMessage["date"])
        userName = jsonMessage["from"] if jsonMessage["from"] else jsonMessage["from_id"]
        text = self.importTextEntities(jsonMessage["text_entities"])

        if "file" in jsonMessage:
            fileName = jsonMessage["file"]
        elif "photo" in jsonMessage:
            fileName = jsonMessage["photo"]
        else:
            fileName = None

        if fileName is not None and self.isAttachmentAvailable(fileName):
            attachment = self.importAttachment(fileName)
        else:
            attachment = None

        self.addMessage((timestamp, userName, text, attachment))

    def importTextEntities(self, textEntities):
        text = ""
        for entity in textEntities:
            entityType = entity["type"]
            if entityType == "bold":
                text += "*"
            elif entityType == "italic":
                text += "_"
            text += entity["text"]
            if entityType == "bold":
                text += "*"
            elif entityType == "italic":
                text += "_"
        return text if len(text)>0 else None

    def isAttachmentAvailable(self, attachmentName):
        return self.fs.hasFile(attachmentName) if self.fs else False

    def importAttachment(self, attachmentName):
        simpleName = self.makeSimpleNameForAttachment(attachmentName)
        return Attachment(self.fs, attachmentName, simpleName)

class TelegramChatExportJsonChat(TelegramJsonChat):
    """
    Load a chat from a JSON file as exported by Telegram Desktop when exporting an individual chat.
    """

    @staticmethod
    def isTelegramChatExportJson(jsonData):
        if isinstance(jsonData, dict):
            return "messages" in jsonData
        return False

    def __init__(self, fs=None):
        # pylint: disable=useless-parent-delegation
        super().__init__(fs)

    def loadMessagesFromJson(self, chatData, fileName=None, chatId=None):
        self.fileName = fileName
        self.groupName = chatData["name"] if chatData["name"] else str(chatData["id"])
        for jsonMessage in chatData["messages"]:
            self.parseAndAddJsonMessage(jsonMessage)

class TelegramDataExportJsonChat(TelegramJsonChat):
    """
    Load a chat from a JSON file as exported by Telegram Desktop when exporting all data.
    """

    @staticmethod
    def isTelegramDataExportJson(jsonData):
        if isinstance(jsonData, dict):
            if "chats" in jsonData:
                if isinstance(jsonData["chats"], dict):
                    return "list" in jsonData["chats"]
        return False

    def __init__(self, fs=None):
        # pylint: disable=useless-parent-delegation
        super().__init__(fs)

    def findChatById(self, chatData, chatId):
        chat = None
        chats = chatData["chats"]["list"]
        found = False
        for chat in chats:
            found = ((chatId is None) or
                     (chat["name"] and chat["name"] == chatId) or
                     (str(chat["id"]) == chatId))
            if found:
                break
        if not found:
            if chatId is None:
                raise Exception("No chats found.")
            else:
                raise Exception("Chat " + chatId + " not found.")
        return chat

    def loadMessagesFromJson(self, chatData, fileName=None, chatId=None):
        if chatId is None and isinstance(fileName, str) and fileName.find("#") != -1:
            fileName, chatId = fileName.split("#")
        chat = self.findChatById(chatData, chatId)
        self.fileName = fileName
        self.groupName = chat["name"] if chat["name"] else str(chat["id"])
        for jsonMessage in chat["messages"]:
            self.parseAndAddJsonMessage(jsonMessage)

class NullChat(Chat):
    """
    Container for an empty chat.
    """
    def __init__(self):
        super().__init__(None)

class FilteredByTime(Chat):
    """
    Filter messages by time.

    We simply iterate over all messages in a chat and import the ones
    within the desired range.
    """

    def __init__(self, otherChat, fromTimestamp=None, toTimestamp=None):
        super().__init__(otherChat.fs)
        self.fileName = otherChat.fileName
        self.otherChat = otherChat
        self.fromDate = fromTimestamp
        self.toTDate = toTimestamp
        self.importMessages(fromTimestamp, toTimestamp)

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

class MergedChat(Chat):
    """
    Merge multiple chats into one timeline.
    """

    # Takes a list of Chat.
    def __init__(self, chats):
        super().__init__(None)
        self.chats = chats
        self.importMessages()
        if len(self.chats) == 0:
            self.fileName = None
        elif len(self.chats) == 1:
            self.fileName = self.chats[0].fileName
        else:
            self.fileName = "(Merged)"

    def importMessage(self, message, index):
        messageData = list(message.data)
        if message.hasAttachment:
            messageData[3] = self.importAttachment(message.attachment)
        if len(self) == 0 or self[-1] != messageData:
            self.addMessage(messageData)

    def importAttachment(self, otherAttachment):
        newName = self.makeSimpleNameForAttachment(otherAttachment.name)
        return Attachment(otherAttachment.fs, otherAttachment.path, newName)

    # Iterate over all messages in all chats, and import them, always
    # selecting the message with the lowest timestamp next.
    def importMessages(self):
        indices = [0] * len(self.chats)
        nextIndex = self.getIndexOfNextMessage(indices)
        while nextIndex is not None:
            message = self.chats[nextIndex][indices[nextIndex]]
            self.importMessage(message, nextIndex)
            indices[nextIndex] += 1
            nextIndex = self.getIndexOfNextMessage(indices)

    # Find the next message, i.e., the one with the lowest timestamp.
    # indices is an array of index values, one for each of the chats.
    def getIndexOfNextMessage(self, indices):
        lowestIndex = None
        lowestTimestamp = None
        # pylint: disable=consider-using-enumerate
        for i in range(len(self.chats)):
            if indices[i] < len(self.chats[i]):
                thisTimestamp = self.chats[i][indices[i]].time
                if (lowestTimestamp is None) or (thisTimestamp < lowestTimestamp):
                    lowestIndex = i
                    lowestTimestamp = thisTimestamp
        return lowestIndex

def openChatFromJson(fs, jsonData, fileName=None, chatId=None):
    if WaceJsonChat.isWaceJson(jsonData):
        chat = WaceJsonChat(fs)
        chat.loadMessagesFromJson(jsonData, fileName, chatId)
    elif TelegramChatExportJsonChat.isTelegramChatExportJson(jsonData):
        chat = TelegramChatExportJsonChat(fs)
        chat.loadMessagesFromJson(jsonData, fileName)
    elif TelegramDataExportJsonChat.isTelegramDataExportJson(jsonData):
        chat = TelegramDataExportJsonChat(fs)
        chat.loadMessagesFromJson(jsonData, fileName, chatId)
    else:
        raise Exception("Unrecognized JSON format.")
    return chat

def openChatUsingJsonStream(fs, stream, fileName=None, chatId=None):
    jsonData = json.load(stream)
    return openChatFromJson(fs, jsonData, fileName, chatId)

def openChatUsingFs(fs, fileName):
    if isinstance(fileName, str) and fileName.find("#") != -1:
        fileName, chatId = fileName.split("#")
    else:
        chatId = None
    if fileName.endswith(".txt"):
        chat = WaChat(fs)
        chat.loadMessagesFromFile(fileName)
    elif fileName.endswith(".json"):
        with fs.openFile(fileName) as stream:
            chat = openChatUsingJsonStream(fs, stream, fileName, chatId)
    else:
        raise Exception("Oops.")
    return chat

def openChatFromZip(fileName, pathInZip=None):
    if pathInZip is None and isinstance(fileName, str) and fileName.find("#") != -1:
        fileName, pathInZip = fileName.split("#")
    fs = ZipFs(fileName)
    if pathInZip:
        chatsInZip = [pathInZip]
    else:
        chatsInZip = fs.findAllChats()
    if len(chatsInZip) == 0:
        raise Exception("No chats found in \"" + str(fileName) + "\".")
    if len(chatsInZip) == 1:
        pathInZip = chatsInZip[0]
        pathAsPath = pathlib.PurePath(pathInZip)
        fs.setPath(pathAsPath.parent)
        return openChatUsingFs(fs, pathAsPath.name)
    return MergedChat([openChatFromZip(fileName, chatInZip) for chatInZip in chatsInZip])

def openChatFromDir(dirName, fileName=None):
    fs = FileFs(dirName)
    if fileName is None:
        chatsInDir = fs.findAllChats()
        if len(chatsInDir) == 0:
            raise Exception("No chats found in \"" + str(dirName) + "\".")
        fileName = chatsInDir[0]
    return openChatUsingFs(fs, fileName)

def openChatFromFile(fileName):
    pathAsPath = pathlib.Path(fileName)
    fs = FileFs(pathAsPath.parent)
    return openChatUsingFs(fs, pathAsPath.name)

def openChatFromStream(file):
    file.seek(0)
    first8Chars = file.read(8)
    file.seek(0)
    if len(first8Chars) > 0 and first8Chars[0] == '{':
        chat = openChatUsingJsonStream(None, file, None)
    else:
        chat = WaChat(None)
        chat.loadMessagesFromStream(file)
    return chat

def openChat(files):
    """
    Generic, flexible open function.

    This function supports:
    - A file name, path-like object or file-like object to either:
      - A ZIP file exported by WhatsApp, or a ZIP file containing
        multiple subdirectories with chats exported by WhatsApp.
      - A "_chat.txt" text file exported by WhatsApp.
      - A JSON file exported by WhatsApp-Chat-Exporter.
    - A file name or path-like object to a directory that contains a
      "_chat.txt" file.
    - None.
    - A list or tuple with a combination of any of the above.

    In any case, it returns a Chat instance.
    """

    if files is None or isinstance(files, (list, tuple)):
        if files is None or len(files) == 0:
            return NullChat()
        elif len(files) == 1:
            return openChat(files[0])
        else:
            return MergedChat([openChat(file) for file in files])

    file = files
    if isinstance(file, io.TextIOBase):
        return openChatFromStream(file)
    elif zipfile.is_zipfile(file):
        return openChatFromZip(file)
    elif isinstance(file, (str, pathlib.Path)):
        path = pathlib.Path(file)
        if path.is_file():
            return openChatFromFile(path)
        elif path.is_dir():
            return openChatFromDir(path)
        else:
            raise Exception("File not found: \"" + str(file) + "\".")
    raise TypeError

def getRawLines(fn):
    """
    For testing and debugging: Get an array of lines from the chat.
    """

    with zipfile.ZipFile(fn) as zipFile:
        with zipFile.open("_chat.txt") as txtFile:
            rawlines = txtFile.read().split(b'\r\n')
    return [rawline.decode() for rawline in rawlines]

def mergeChats(outputFile, chatFiles, verbose):
    """
    Allow merging chats from the command line.
    """

    chats = list()
    for fn in chatFiles:
        if verbose:
            print("Loading \"" + fn + "\" ... ", end="", flush=True)
        chat = openChat(fn)
        if verbose:
            print("{0} messages loaded.".format(len(chat)))
        chats.append(chat)

    if verbose:
        print("Merging ... ", end="", flush=True)
    mergedChat = MergedChat(chats)
    if verbose:
        print("{0} messages merged.".format(len(mergedChat)))

    if verbose:
        print("Exporting \"" + outputFile + "\" ... ", end="", flush=True)
    mergedChat.exportToZip(outputFile)
    if verbose:
        print("done.")

def mergeChatsCli():
    # pylint: disable=import-outside-toplevel
    import argparse
    import glob
    parser = argparse.ArgumentParser(prog="WhatsApp Chat Merger")
    parser.add_argument('--outputFile', default=None, help="Tie Zip file to write the merged chat to.")
    parser.add_argument('-v', '--verbose', default=False, action=argparse.BooleanOptionalAction, help="Print information about progress.")
    parser.add_argument('chats', nargs="+", default=[], help="Chats to import.")
    args = parser.parse_args()
    chatFiles = list()
    for chat in args.chats:
        chatFiles.extend(glob.glob(chat))
    mergeChats(args.outputFile, chatFiles, args.verbose)

if __name__ == "__main__":
    mergeChatsCli()
