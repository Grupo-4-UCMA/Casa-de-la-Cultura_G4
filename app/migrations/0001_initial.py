import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Author',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Genre',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='LibraryUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField(unique=True)),
                ('birth_date', models.DateField(blank=True, null=True)),
                ('comment', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('book_id', models.IntegerField(unique=True)),
                ('title', models.CharField(max_length=500)),
                ('original_title', models.CharField(blank=True, max_length=500, null=True)),
                ('isbn', models.CharField(blank=True, max_length=20, null=True)),
                ('publication_year', models.IntegerField(blank=True, null=True)),
                ('language_code', models.CharField(blank=True, max_length=10, null=True)),
                ('image_url', models.URLField(blank=True, null=True)),
                ('authors', models.ManyToManyField(related_name='books', to='app.author')),
                ('genres', models.ManyToManyField(blank=True, related_name='books', to='app.genre')),
            ],
        ),
        migrations.CreateModel(
            name='Copy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('copy_id', models.IntegerField(unique=True)),
                ('available', models.BooleanField(default=True)),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='copies', to='app.book')),
            ],
        ),
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('copy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='app.copy')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='app.libraryuser')),
            ],
            options={
                'indexes': [
                    models.Index(fields=['user'], name='app_rat_user_id_idx'),
                    models.Index(fields=['copy'], name='app_rat_copy_id_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='Recommendation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.FloatField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.book')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recommendations', to='app.libraryuser')),
            ],
            options={
                'unique_together': {('user', 'book')},
            },
        ),
    ]