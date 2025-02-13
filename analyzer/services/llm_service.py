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

    def _chunk_products(self, products: List[Product], chunk_size: int = 5) -> List[List[Product]]:
        """Split products into smaller chunks for efficient processing"""
        if not products:
            return []
            
        # For the last chunk, reduce size if it's too close to the full chunk size
        if len(products) % chunk_size == 3:  # If last chunk would be size 3
            chunk_size = 3  # Reduce chunk size to avoid context limit
            
        return [products[i:i + chunk_size] for i in range(0, len(products), chunk_size)]

    def _generate_product_summaries(self, products_data: List[Dict]) -> List[Dict]:
        """Generate summaries for a batch of products"""
        expected_format = [
            {
                "uuid": "product-uuid",
                "summary": "Product summary text"
            }
        ]
        
        # Simplified prompt to reduce token count
        prompt = f"""
        Generate concise summaries (max 75 words each) for these products, highlighting key features and value:

        Products:
        {json.dumps(products_data, indent=2)}
        """
        
        try:
            return self.client.generate_structured_completion(
                prompt=prompt,
                expected_format=expected_format,
                temperature=0.3,
                max_tokens=800  # Adjust based on your needs
            )
        except Exception as e:
            logger.error(f"Error generating summaries for chunk: {str(e)}")
            # Handle the last chunk specially if it fails
            if len(products_data) > 2:
                logger.info("Retrying with smaller chunk size")
                # Split the chunk and try again
                mid = len(products_data) // 2
                first_half = self._generate_product_summaries(products_data[:mid])
                second_half = self._generate_product_summaries(products_data[mid:])
                if first_half and second_half:
                    return first_half + second_half
            return None

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
        Respond with a valid JSON object containing exactly three trends and a summary.
        Each trend must have a title, description, and supporting_data as strings.
        Do not include any explanatory text outside the JSON structure.
        """
        
        return self.client.generate_structured_completion(
            prompt=prompt,
            expected_format=expected_format,
            temperature=0.2
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
        chunks = self._chunk_products(products)
        total_chunks = len(chunks)
        
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"Processing chunk {i} of {total_chunks}")
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
            else:
                logger.warning(f"Failed to process chunk {i}")

        # Update product summaries
        successful_updates = 0
        for summary in all_summaries:
            try:
                Product.objects.filter(uuid=summary['uuid']).update(
                    ai_summary=summary['summary']
                )
                successful_updates += 1
            except Exception as e:
                logger.error(f"Error updating product {summary['uuid']}: {str(e)}")

        logger.info(f"Successfully updated {successful_updates} product summaries")

        # Generate trends analysis using minimal data for efficiency
        trends_data = [{
            'name': p.name[:20], # take only first 20 characters of name for efficiency
            'price': float(p.price),
            'rating': float(p.rating) if p.rating else None
        } for p in products]  # Only send necessary fields for trend analysis

        trends_analysis = self._analyze_product_trends(trends_data)

        if trends_analysis:
            search_key = products[0].search_key if products else "laptops"
            trend = ProductTrend.objects.create(
                trend_analysis=trends_analysis,
                search_key=search_key
            )
            return trend.to_dict()

        return None 