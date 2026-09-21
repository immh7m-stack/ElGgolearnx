from .archive import ArchiveBookProvider
from .doi import DoiBookProvider
from .google_books import GoogleBooksProvider
from .openlibrary import OpenLibraryProvider
from .pdf import PdfBookProvider
from .remote_html import RemoteHtmlProvider

__all__ = [
    "ArchiveBookProvider",
    "DoiBookProvider",
    "GoogleBooksProvider",
    "OpenLibraryProvider",
    "PdfBookProvider",
    "RemoteHtmlProvider",
]
