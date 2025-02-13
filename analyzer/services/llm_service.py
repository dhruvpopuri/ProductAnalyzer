import logging
from typing import List, Dict
from django.db import transaction
from .groq_client import GroqClient
from ..models import Product, ProductTrend
import json

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = GroqClient()

    def _chunk_products(self, products: List[Product], chunk_size: int = 4) -> List[List[Product]]:
        """Split products into smaller chunks for efficient processing"""
        return [products[i:i + chunk_size] for i in range(0, len(products), chunk_size)]

    def _generate_product_summaries(self, products_data: List[Dict]) -> List[Dict]:
        """Generate summaries for a batch of products"""
        expected_format = [
            {
                "uuid": "product-uuid",
                "summary": "Product summary text"
            }
        ]
        
        prompt = f"""
        For each product in the following list, generate a concise summary highlighting key features and value proposition.
        Keep each summary under 100 words.
        
        Products:
        {json.dumps(products_data, indent=2)}
        """
        
        return self.client.generate_structured_completion(
            prompt=prompt,
            expected_format=expected_format,
            temperature=0.3
        )

    def _analyze_product_trends(self, products_data: List[Dict]) -> Dict:
        """Analyze trends in product data"""
        expected_format = {
            "trends": [
                {
                    "title": "Example trend title",
                    "description": "Trend description",
                    "supporting_data": "Statistical evidence"
                }
            ],
            "summary": "Overall market analysis"
        }
        
        prompt = f"""
        Analyze the following product dataset and identify the top 3 trends based on pricing and ratings.
        Focus on:
        1. Price ranges and clusters
        2. Price-to-rating relationships
        3. Common features across price points
        
        Products:
        {json.dumps(products_data, indent=2)}
        """
        
        return self.client.generate_structured_completion(
            prompt=prompt,
            expected_format=expected_format,
            temperature=0.3
        )

    @transaction.atomic
    def process_products(self, products: List[Product] = None) -> Dict:
        """
        Process products and generate summaries and trends
        
        Args:
            products: List of products to process. If None, processes all products without summaries.
        """
        if not products:
            logger.info("No products to process")
            return None

        # Generate summaries in batches
        all_summaries = []
        for chunk in self._chunk_products(products):
            products_data = [{
                'uuid': str(p.uuid),
                'name': p.name,
                'description': p.description,
                'price': float(p.price),
                'rating': float(p.rating) if p.rating else None
            } for p in chunk]

            summaries = self._generate_product_summaries(products_data)
            if summaries:
                all_summaries.extend(summaries)

        # Update product summaries
        for summary in all_summaries:
            Product.objects.filter(uuid=summary['uuid']).update(
                ai_summary=summary['summary']
            )

        # Generate trends analysis using products with the same search key
        products_data = [{
            'name': p.name,
            'price': float(p.price),
            'rating': float(p.rating) if p.rating else None
        } for p in products]

        trends_analysis = self._analyze_product_trends(products_data)
        
        if trends_analysis:
            trend = ProductTrend.objects.create(
                trend_analysis=trends_analysis
            )
            return trend.to_dict()

        return None 