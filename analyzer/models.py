import uuid
from django.db import models
from django.utils import timezone

class BaseModel(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Product(BaseModel):
    name = models.CharField(max_length=1000)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True)
    description = models.TextField()
    url = models.URLField(max_length=4000)
    ai_summary = models.TextField(null=True, blank=True)
    search_key = models.CharField(max_length=450, default="laptops")

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['price']),
            models.Index(fields=['rating']),
        ]

    def to_dict(self):
        return {
            'uuid': str(self.uuid),
            'name': self.name,
            'price': float(self.price),
            'rating': float(self.rating) if self.rating else None,
            'description': self.description,
            'url': self.url,
            'ai_summary': self.ai_summary,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class ProductTrend(BaseModel):
    trend_date = models.DateField(auto_now_add=True)
    trend_analysis = models.JSONField()

    class Meta:
        get_latest_by = 'created_at'

    def to_dict(self):
        return {
            'uuid': str(self.uuid),
            'trend_date': self.trend_date.isoformat(),
            'trend_analysis': self.trend_analysis,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
