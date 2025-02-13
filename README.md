# Product Analyzer

A Django-based web application that scrapes product data from Amazon, generates AI-powered summaries using Groq LLM, and provides insights about product trends and pricing patterns.

## Features
- Amazon product scraping with retry logic and rate limiting
- AI-powered product summaries using Llama-3.2-3b-preview
- Automated trend analysis and insights
- RESTful API with Swagger documentation
- Efficient batch processing for large datasets

## Prerequisites
- Docker and Docker Compose
- Groq API key (sign up at https://console.groq.com)

## Project Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ProductAnalyzer
   ```

2. **Environment Setup:**
   
   Create a `.env` file in the root directory:
   ```env
   # Django settings
   DEBUG=True
   SECRET_KEY=your-secret-key-here
   DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1]

   # Database settings
   POSTGRES_DB=product_analyzer
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   DATABASE_HOST=db
   DATABASE_PORT=5432

   # Groq API settings
   GROQ_API_KEY=your-groq-api-key-here
   ```

3. **Build and Start Services:**
   ```bash
   # Build the Docker images
   docker-compose build

   # Start the services and run the entrypoint
   docker compose up --build -d
   ```

The application will be available at `http://localhost:8000`

## API Endpoints

Visit `http://localhost:8000/swagger/` for interactive API documentation and testing.

### Quick Endpoint Overview:
- `POST /api/scrape/` - Scrape products from Amazon (accepts search_term and max_pages)
- `POST /api/process/` - Generate AI summaries and trend analysis for products for a given search_term that you scraped.
- `GET /api/products/` - List all scraped products with pagination
- `GET /api/products/{uuid}/` - Get detailed product information
- `GET /api/insights/` - Get AI-generated trends and market analysis for a given search_term.


## Development Notes
- The scraping may take upto 5-10 minutes depending upon the number of pages (each page has around 15-20 unique items), as I have chosen to scrape from amazon for a more relatable real-life use-case, and have implemented a variety of strategies such as User-Agent rotation, exponential backoff etc in order to scrape from it.
- LLM processing is done in configurable batches (default: 5 products per batch, as the context size for the free tier may be exceeded). Each batch takes almost 35-50 seconds in order to be processed.
- All operations are logged to `django.log` for debugging
- Database operations use transactions to ensure data consistency
- All of the above APIs can be tested and viewed from the /swagger/ subpath (http://localhost:8000/swagger/).
- Used to_dict methods on models instead of serializers for performance considerations

## Monitoring and Logs
- Application logs are written to `django.log`
- Docker logs can be viewed using:
  ```bash
  docker logs -f productanalysis-web-1
  ```

## Using Swagger to Test the endpoints
- Go to http://localhost:8000/swagger/
- First go to the scrape API and click on the drop-down and click on try it out. Modify and set the number of pages and the search term according to your preferences.
- Next go to the process drop-down and click on try it out, there you can set the search key for which you want to process the insights from the scraped data.
- Then you can use the various get APIs (via Swagger try-it-out) to get the data.
- Added pagination for the list products API, so specify the pages, and num items per page.
- Please note for some of the extremely long running requests, swagger might not show the response, so please use a python script with long request timeout.

## Testing notes
- To simplify and reduce testing time , I have compiled scraped data in products_backup.json (about 200 laptop products), you can restore the products into the db using the command `sudo docker exec -t productanalysis-web-1 python restore_product_data.py`. Then you can run the process API with the search term `laptops` to inference with the LLM and store the trends data.
- In case you want to use any other search key, you may scrape the data using the scrape endpoint (which takes 5-7 seconds per listing), and subsequently use that search term for the process and insight endpoints.