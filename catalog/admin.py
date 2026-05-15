from django.contrib import admin
from .models import (
    Author,
    Genre,
    Book,
    Copy,
    LibraryUser,
    Rating,
    Recommendation
)

admin.site.register(Author)
admin.site.register(Genre)
admin.site.register(Book)
admin.site.register(Copy)
admin.site.register(LibraryUser)
admin.site.register(Rating)
admin.site.register(Recommendation)