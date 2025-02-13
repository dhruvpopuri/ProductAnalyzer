import requests
from bs4 import BeautifulSoup
import time
import logging
import random
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class AmazonScraper:
    BASE_URL = "https://www.amazon.in/s"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        # Rotate between different user agents
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        ]

    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    def _make_request(self, url: str, params: dict = None) -> requests.Response:
        """Make a request with retry logic and random delays"""
        # Rotate user agent to avoid 503 or rate limit issues
        self.session.headers['User-Agent'] = random.choice(self.user_agents)

        # Add random delay
        time.sleep(random.uniform(1, 2))
        
        response = self.session.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        if 'To discuss automated access to Amazon data please contact' in response.text:
            raise requests.exceptions.HTTPError('Amazon is blocking automated access')
            
        return response

    def get_product_links(self, search_term: str = 'laptops', max_pages: int = 1) -> list:
        """Get product links from search results"""
        product_links = []
        
        for page in range(1, max_pages + 1):
            try:
                params = {
                    'k': search_term,
                    'page': page,
                    'ref': 'sr_pg_' + str(page)
                }
                
                response = self._make_request(self.BASE_URL, params=params)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find all product links
                products = soup.find_all('a', {'class': 'a-link-normal s-no-outline'})
                
                for product in products:
                    href = product.get('href')
                    if href and '/dp/' in href:
                        full_url = 'https://www.amazon.in' + href if not href.startswith('http') else href
                        product_links.append(full_url)
                
                logger.info(f"Found {len(products)} products on page {page}")
                
            except Exception as e:
                logger.error(f"Error scraping page {page}: {str(e)}")
                continue
        
        return list(set(product_links))  # Remove duplicates

    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    def scrape_product(self, url: str, search_term: str) -> dict:
        """Scrape product details"""
        try:
            response = self._make_request(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract product details
            name = soup.find('span', {'id': 'productTitle'})
            name = name.text.strip() if name else None
            
            price = soup.find('span', {'class': 'a-price-whole'})
            price = float(price.text.replace(',', '').strip()) if price else None
            
            rating = soup.find('span', {'class': 'a-icon-alt'})
            if rating and 'out of 5 stars' in rating.text:
                rating = float(rating.text.split()[0])
            else:
                rating = None
            
            description = soup.find('div', {'id': 'feature-bullets'})
            description = description.text.strip() if description else None
            
            if not all([name, price, description]):
                logger.warning(f"Missing required fields for product: {url}")
                return None
            
            return {
                'name': name,
                'price': price,
                'rating': rating,
                'description': description,
                'url': url,
                'search_key': search_term
            }
            
        except Exception as e:
            logger.error(f"Error scraping product {url}: {str(e)}")
            return None