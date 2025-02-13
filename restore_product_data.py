import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ProductAnalyzer.ProductAnalyzer.settings")  # Replace with your actual project name
django.setup()

from analyzer.models import Product  # Now you can import Django models
import json

# Load from JSON file
with open("products_backup.json", "r") as f:
    products_list = json.load(f)

# Restore products
for product_data in products_list:
    product_data.pop("uuid", None)  # Remove UUID if auto-generated
    product_data.pop("created_at", None)  # Remove timestamps if auto-generated
    product_data.pop("updated_at", None)

    Product.objects.create(**product_data)

print("Products restored successfully!")
