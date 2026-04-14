import uuid6
from django.db import models
from django.utils import timezone

class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    gender = models.CharField(max_length=50)
    gender_probability = models.FloatField()
    sample_size = models.IntegerField()
    age = models.IntegerField()
    age_group = models.CharField(max_length=50)
    country_id = models.CharField(max_length=10)
    country_probability = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.id}"
