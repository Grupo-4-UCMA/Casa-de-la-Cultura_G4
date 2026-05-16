from django.db import models

class Libro(models.Model):
    book_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20)
    publication_year = models.IntegerField()
    genre = models.CharField(max_length=100)