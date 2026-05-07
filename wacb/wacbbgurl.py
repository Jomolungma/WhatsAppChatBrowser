import threading
import urllib.request

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

#
# Small helpers to download URLs in the background, using a separate thread.
#

class BgUrlDownloader:
    bytesToReadEachTime = 1024

    def __init__(self, url, callback=None):
        self.url = url
        self.data = b''
        self.success = False
        self.thread = None
        self.http = None
        self.canceled = False
        self.running = True
        self.callback = callback
        self.name = BgUrlDownloader.getNameForUrl(self.url)
        self.thread = threading.Thread(target=self.download)
        self.thread.start()

    def getNameForUrl(url):
        splitUrl = url.split("/")
        if len(splitUrl) > 1 and len(splitUrl[-1]) != 0:
            name = splitUrl[-1]
        elif len(splitUrl) > 2 and len(splitUrl[-2]) != 0:
            name = splitUrl[-2]
        else:
            name = url
        pos = name.find("#")
        if pos != -1:
            name = name[:pos]
        pos = name.find("?")
        if pos != -1:
            name = name[:pos]
        return name

    def __del__(self):
        self.close()

    def __bool__(self):
        return self.success

    def __len__(self):
        return len(self.data)

    @property
    def done(self):
        return not self.running

    def get(self):
        return self.data

    def cancel(self):
        self.canceled = True

    def close(self):
        if self.thread and self.thread != threading.current_thread():
            self.thread.join()
            self.thread = None
        if self.http:
            self.http.close()

    def wait(self):
        if self.running:
            self.close()

    def downloadFinished(self, success):
        self.success = success
        self.running = False
        if self.callback:
            self.callback()

    def download(self):
        try:
            self.http = urllib.request.urlopen(self.url)
        except:
            self.downloadFinished(False)
            return

        if self.http.status != 200:
            self.downloadFinished(False)
            return

        try:
            moreData = self.http.read(BgUrlDownloader.bytesToReadEachTime)
            while len(moreData) > 0 and not self.canceled and not self.http.closed:
                self.data += moreData
                moreData = self.http.read(BgUrlDownloader.bytesToReadEachTime)
        except:
            self.canceled = True

        self.http.close()
        self.downloadFinished(not self.canceled)

class BgUrlsIterator:
    def __init__(self, downloader):
        self.downloader = downloader
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.downloader):
            raise StopIteration
        this = self.downloader[self.index]
        self.index += 1
        return this

class BgUrlsDownloader:
    def __init__(self, urls, callback=None):
        self.index = 0
        self.urls = urls
        self.canceled = False
        self.running = True
        self.downloads = [None for i in range(len(urls))]
        self.callback = callback
        self.startDownload()

    def __bool__(self):
        success = True
        for download in self.downloads:
            if (download == None) or not bool(download):
                success = False
        return success

    def __len__(self):
        return len(self.urls)

    def __iter__(self):
        return BgUrlsIterator(self)

    def __contains__(self, index):
        return (index >= 0) and (index < len(self.urls))

    def __getitem__(self, index):
        if index >= len(self.urls):
            raise IndexError
        return self.downloads[index]

    @property
    def done(self):
        return not self.running

    def cancel(self):
        self.canceled = True
        if self.running:
            self.downloads[self.index].cancel()

    def wait(self):
        while self.running:
            if self.index >= len(self.urls):
                return
            self.downloads[self.index].wait()

    def startDownload(self):
        if (self.index < len(self.urls)) and not self.canceled:
            url = self.urls[self.index]
            self.downloads[self.index] = BgUrlDownloader(url, self.downloadFinished)
        elif self.running:
            self.running = False
            if self.callback:
                self.callback()

    def downloadFinished(self):
        if not self.running or self.canceled:
            return
        if self.downloads[self.index] == None:
            return
        if self.downloads[self.index].done:
            self.index += 1
            self.startDownload()

    def getCurrentName(self):
        if not self.running:
            return ""
        return self.downloads[self.index].name

    def getCurrentBytes(self):
        if not self.running:
            return 0
        return len(self.downloads[self.index])

