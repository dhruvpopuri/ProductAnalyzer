import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator
from django.db import transaction

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Product, ProductTrend
from .services.llm_service import LLMService
from .management.commands.run_scraper import AmazonScraper

logger = logging.getLogger(__name__)

# Create your views here.

class BaseAPIView(APIView):
    def json_response(self, data, status=status.HTTP_200_OK):
        return Response(
            data,
            status=status
        )

class ProductListView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve a list of products",
        manual_parameters=[
            openapi.Parameter(
                'page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, default=1
            ),
            openapi.Parameter(
                'page_size', openapi.IN_QUERY, description="Number of products per page", type=openapi.TYPE_INTEGER, default=20
            ),
        ],
        responses={200: openapi.Response('List of products', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                'current_page': openapi.Schema(type=openapi.TYPE_INTEGER),
                'results': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT))
            }
        ))}
    )
    def get(self, request):
        try:
            page = request.GET.get('page', 1)
            page_size = request.GET.get('page_size', 20)
            
            products = Product.objects.all().order_by('-created_at')
            paginator = Paginator(products, page_size)
            
            current_page = paginator.page(page)
            return self.json_response({
                'total': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': int(page),
                'results': [product.to_dict() for product in current_page]
            })
        except Exception as e:
            logger.error(f"Error retrieving product list: {str(e)}")
            return self.json_response({'error': 'An error occurred'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProductDetailView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve a product by UUID",
        responses={200: openapi.Response('Product details', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'uuid': openapi.Schema(type=openapi.TYPE_STRING),
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'price': openapi.Schema(type=openapi.TYPE_NUMBER),
                'rating': openapi.Schema(type=openapi.TYPE_NUMBER, format='float'),
                'description': openapi.Schema(type=openapi.TYPE_STRING),
                'url': openapi.Schema(type=openapi.TYPE_STRING, format='url'),
                'ai_summary': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time')
            }
        ))}
    )
    def get(self, request, uuid):
        try:
            product = Product.objects.get(uuid=uuid)
            return self.json_response(product.to_dict())
        except Product.DoesNotExist:
            logger.warning(f"Product with UUID {uuid} not found")
            return self.json_response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving product details: {str(e)}")
            return self.json_response({'error': 'An error occurred'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProductInsightsView(BaseAPIView):
    @swagger_auto_schema(
        operation_description="Retrieve AI-generated product insights and trends",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'search_key': openapi.Schema(type=openapi.TYPE_STRING, default='laptops'),
            },
            required=['search_key']
        ),
        responses={
            200: openapi.Response('Product insights', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'trends': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'title': openapi.Schema(type=openapi.TYPE_STRING),
                                'description': openapi.Schema(type=openapi.TYPE_STRING),
                                'supporting_data': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        )
                    ),
                    'summary': openapi.Schema(type=openapi.TYPE_STRING),
                    'latest_analysis_date': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                }
            ))
        }
    )
    def post(self, request):
        try:
            search_key = request.data.get('search_key', 'laptops')
            latest_trend = ProductTrend.objects.filter(
                product__search_key=search_key
            ).latest('created_at')
            
            return self.json_response({
                **latest_trend.trend_analysis,
                'latest_analysis_date': latest_trend.created_at.isoformat()
            })
        except ProductTrend.DoesNotExist:
            logger.error(f"No insights available for search key: {search_key}")
            return self.json_response({'error': 'No insights available'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving insights: {str(e)}")
            return self.json_response({'error': 'An error occurred'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ScrapingView(APIView):
    @swagger_auto_schema(
        operation_description="Trigger product scraping from Amazon",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'search_term': openapi.Schema(type=openapi.TYPE_STRING, default='laptops'),
                'max_pages': openapi.Schema(type=openapi.TYPE_INTEGER, default=1),
            },
            required=['search_term']
        ),
        responses={
            200: openapi.Response('Scraping results', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'products_scraped': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            ))
        }
    )
    def post(self, request):
        try:
            search_term = request.data.get('search_term', 'laptops')
            max_pages = int(request.data.get('max_pages', 1))
            
            scraper = AmazonScraper()
            product_links = scraper.get_product_links(
                search_term=search_term,
                max_pages=max_pages
            )
            
            successful_scrapes = 0
            logger.info(f"Received total of {len(product_links)} product links from scrape")
            with transaction.atomic():
                for url in product_links:
                    try:
                        product_data = scraper.scrape_product(url, search_term)
                        if product_data:
                            p = Product.objects.create(**product_data)
                            successful_scrapes += 1
                            logger.info(f"Scraped {successful_scrapes}")
                    except Exception as e:
                        logger.error(f"Error scraping product {url}: {str(e)}")
                        continue
            
            return Response({
                'message': 'Scraping completed successfully',
                'products_scraped': successful_scrapes
            })
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            return Response(
                {'error': 'An error occurred during scraping'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ProcessProductsView(APIView):
    @swagger_auto_schema(
        operation_description="Process products with LLM for summaries and trends",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'search_key': openapi.Schema(type=openapi.TYPE_STRING, default='laptops'),
            },
            required=['search_key']
        ),
        responses={
            200: openapi.Response('Processing results', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'trends': openapi.Schema(type=openapi.TYPE_OBJECT),
                }
            ))
        }
    )
    def post(self, request):
        try:
            search_key = request.data.get('search_key', 'laptops')
            llm_service = LLMService()
            products = Product.objects.filter(ai_summary__isnull=True, search_key=search_key)
            trends = llm_service.process_products(products=products)

            return Response({
                'message': 'Products processed successfully',
                'trends': trends
            })
        except Exception as e:
            logger.error(f"Error processing products: {str(e)}")
            return Response(
                {'error': 'An error occurred during processing'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
