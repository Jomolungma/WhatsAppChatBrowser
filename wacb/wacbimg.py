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

import struct

#
# Helper function to read image dimensions from a file.
#
# The getImageTypeFromFile() and getImageSize() functions take a binary stream
# parameter. The stream must be seekable. The stream is left at an undefined
# position upon return.
#

class ImageHelper:
    pngSignature = bytearray([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
    pngIhdrChunkFormat = struct.Struct(">I4sII5x4x")

    # io.RawIOBase.read() may read fewer bytes when at EOF. When fewer bytes are
    # read than expected, struct.unpack() fails. To guard against broken or truncated
    # files, this helper always returns the exact number of bytes requested.
    def read(file, count):
        data = file.read(count)
        while len(data) < count:
            data += b'\0'
        return data

    def isPngFile(first8Bytes):
        return first8Bytes == ImageHelper.pngSignature

    def pngImageSize(file, first8Bytes):
        firstChunk = ImageHelper.read(file, 25)
        if len(firstChunk) == 25:
            chunkLength, chunkType, imageWidth, imageHeight = ImageHelper.pngIhdrChunkFormat.unpack(firstChunk)
            if chunkType == b'IHDR':
                return imageWidth, imageHeight
        return None, None

    jpegSoiAndApp0Marker = bytearray([255, 216, 255, 224])
    jpegExtractSegmentLengthFromFirst8Bytes = struct.Struct(">xxxxHxx")
    jpegExtractSegmentHeader = struct.Struct(">2sH")
    jpegExtractDataFromSegment = struct.Struct(">xHH")

    def isJpegFile(first8Bytes):
        return first8Bytes[0:4] == ImageHelper.jpegSoiAndApp0Marker

    def jpegImageSize(file, first8Bytes):
        app0Length = ImageHelper.jpegExtractSegmentLengthFromFirst8Bytes.unpack(first8Bytes)[0]
        file.seek(app0Length - 4, 1)
        segmentHeader = ImageHelper.read(file, 4)
        while len(segmentHeader) == 4:
            segMarker, segLength = ImageHelper.jpegExtractSegmentHeader.unpack(segmentHeader)
            if segMarker[0] == 255 and segMarker[1] >= 192 and segMarker[1] <= 195:
                segmentData = ImageHelper.read(file, 5)
                imageHeight, imageWidth = ImageHelper.jpegExtractDataFromSegment.unpack(segmentData)
                return imageWidth, imageHeight
            elif segMarker[0] != 255 or segMarker[1] == 218:
                # If segMarker[0] != 255, then the file has an unexpected structure and might be broken.
                # If segMarker[1] == 218, then we are at start-of-stream, and we should look no further.
                break
            file.seek(segLength - 2, 1)
            segmentHeader = ImageHelper.read(file, 4)
        return None, None

    webpFileHeader = b'RIFF'
    webpExtractFirstChunkHeader = struct.Struct("<4s4sI")
    webpExtractVp8xChunkData = struct.Struct("<xxxxhxhx")
    webpExtractVp8lChunkData = struct.Struct("<I")
    webpExtractVp8ChunkData = struct.Struct("<hx3shh")

    def isWebpFile(first8Bytes):
        return first8Bytes[0:4] == ImageHelper.webpFileHeader

    def webpImageSize(file, first8Bytes):
        firstChunkHeader = ImageHelper.read(file, 12)
        webpMarker, chunkType, chunkLength = ImageHelper.webpExtractFirstChunkHeader.unpack(firstChunkHeader)
        if webpMarker != b'WEBP':
            return None, None
        if chunkType == b'VP8X' and chunkLength == 10:
            firstChunkData = ImageHelper.read(file, 10)
            # Width and height are 24 bit numbers. We only look at the lower 16 bits.
            canvasWidthMinusOne, canvasHeightMinusOne = ImageHelper.webpExtractVp8xChunkData.unpack(firstChunkData)
            return canvasWidthMinusOne+1, canvasHeightMinusOne+1
        elif chunkType == b'VP8L' and chunkLength > 4:
            firstChunkData = ImageHelper.read(file, 5)
            widthAndHeight = ImageHelper.webpExtractVp8lChunkData(firstChunkData[1:5])
            imageWidth = (widthAndHeight & 0x3fff) + 1
            imageHeight = ((widthAndHeight >> 14) & 0x3fff) + 1
            return imageWidth, imageHeight
        elif chunkType == b'VP8 ' and chunkLength > 10:
            firstChunkData = ImageHelper.read(file, 10)
            frameTag, startCode, hsc, vsc = ImageHelper.webpExtractVp8ChunkData.unpack(firstChunkData)
            if (frameTag & 1) == 1 and startCode == b'\x9d\x01\x2a':
                imageWidth = hsc & 0x3fff
                imageHeight = vsc & 0x3fff
                return imageWidth, imageHeight
        return None, None

    def getImageTypeFromFirst8Bytes(first8Bytes):
        if ImageHelper.isPngFile(first8Bytes):
            return "image/png"
        elif ImageHelper.isJpegFile(first8Bytes):
            return "image/jpeg"
        elif ImageHelper.isWebpFile(first8Bytes):
            return "image/webp"
        return None

    def getImageTypeFromFile(file):
        file.seek(0)
        first8Bytes = ImageHelper.read(file, 8)
        return ImageHelper.getImageTypeFromFirst8Bytes(first8Bytes)

    def getImageSizeFromFile(file):
        file.seek(0)
        first8Bytes = ImageHelper.read(file, 8)
        if ImageHelper.isPngFile(first8Bytes):
            return ImageHelper.pngImageSize(file, first8Bytes)
        elif ImageHelper.isJpegFile(first8Bytes):
            return ImageHelper.jpegImageSize(file, first8Bytes)
        elif ImageHelper.isWebpFile(first8Bytes):
            return ImageHelper.webpImageSize(file, first8Bytes)
        return None, None

    def getImageTypeAndSizeFromFile(file):
        file.seek(0)
        first8Bytes = ImageHelper.read(file, 8)
        imageType = ImageHelper.getImageTypeFromFirst8Bytes(first8Bytes)
        if ImageHelper.isPngFile(first8Bytes):
            imageWidth, imageHeight = ImageHelper.pngImageSize(file, first8Bytes)
        elif ImageHelper.isJpegFile(first8Bytes):
            imageWidth, imageHeight = ImageHelper.jpegImageSize(file, first8Bytes)
        elif ImageHelper.isWebpFile(first8Bytes):
            imageWidth, imageHeight = ImageHelper.webpImageSize(file, first8Bytes)
        else:
            imageWidth, imageHeight = None, None
        return imageType, imageWidth, imageHeight

    def getImageTypeFromFileName(name):
        with open(name, "rb") as file:
            return ImageHelper.getImageTypeFromFile(file)

    def getImageSizeFromFileName(name):
        with open(name, "rb") as file:
            return ImageHelper.getImageSizeFromFile(file)

    def getImageTypeAndSizeFromFileName(name):
        with open(name, "rb") as file:
            return ImageHelper.getImageTypeAndSizeFromFile(file)
