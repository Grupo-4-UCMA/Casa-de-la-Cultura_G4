from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    book_id = models.IntegerField(unique=True)

    title = models.CharField(max_length=500)
    original_title = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )

    isbn = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    publication_year = models.IntegerField(
        blank=True,
        null=True
    )

    language_code = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )

    image_url = models.URLField(
        blank=True,
        null=True
    )

    authors = models.ManyToManyField(
        Author,
        related_name="books"
    )

    genres = models.ManyToManyField(
        Genre,
        related_name="books",
        blank=True
    )

    def __str__(self):
        return self.title


class Copy(models.Model):
    copy_id = models.IntegerField(unique=True)

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="copies"
    )

    available = models.BooleanField(default=True)

    def __str__(self):
        return f"Copy {self.copy_id}"


class LibraryUser(models.Model):
    user_id = models.IntegerField(unique=True)

    birth_date = models.DateField(
        blank=True,
        null=True
    )

    comment = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):
        return f"User {self.user_id}"


class Rating(models.Model):
    user = models.ForeignKey(
        LibraryUser,
        on_delete=models.CASCADE,
        related_name="ratings"
    )

    copy = models.ForeignKey(
        Copy,
        on_delete=models.CASCADE,
        related_name="ratings"
    )

    rating = models.IntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = ("user", "copy")
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["copy"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.rating}"


class Recommendation(models.Model):
    user = models.ForeignKey(
        LibraryUser,
        on_delete=models.CASCADE,
        related_name="recommendations"
    )

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE
    )

    score = models.FloatField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = ("user", "book")

    def __str__(self):
        return f"{self.user} -> {self.book}"