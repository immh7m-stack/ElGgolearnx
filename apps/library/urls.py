from django.urls import path

from . import views

app_name = "library"

urlpatterns = [
    path("search/", views.search_page, name="search"),
    path("search/api/", views.search_api, name="search_api"),
    path("sites/", views.sites_page, name="sites"),
    path("my/", views.my_library, name="my_library"),
    path("history/", views.history_page, name="history"),
    path("watch/", views.watch_playlist, name="watch"),
    path("read-book/", views.read_book_page, name="read_book"),
    path("read-pdf/", views.read_remote_pdf, name="read_pdf"),
    path("google-books-viewer/", views.google_books_viewer, name="google_books_viewer"),
    path("save-playlist/", views.save_playlist, name="save_playlist"),
    path("save-book/", views.save_book, name="save_book"),
    path("download/start/", views.start_download_view, name="start_download"),
    path("download/<int:job_id>/cancel/", views.cancel_download_view, name="cancel_download"),
    path("download/<int:job_id>/delete/", views.delete_download_job_view, name="delete_download"),
    path("download/<int:job_id>/status/", views.download_status, name="download_status"),
    path("download-book/", views.download_book, name="download_book"),
]