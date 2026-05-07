import io
from wacb import wacbapp
from .wacbtesthelpers import *

def test_exportHtml():
    app = makeTestApp()
    stream = io.BytesIO()
    app.exportToZip(stream)
    app.close()
