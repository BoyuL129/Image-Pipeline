from typing import Optional
import redis
import hashlib
import json
import asyncio
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from fastapi.param_functions import Query
from models.search_models import SearchRequest, SearchResult
from services.image_service import ImageService
from services.search_service import SearchService
from services.matching_service import MatchingService

app = FastAPI()

redis_client = redis.StrictRedis(
    host='0.0.0.0', port=6379, db=0, decode_responses=True)


# Initialize services
image_service = ImageService()
search_service = SearchService()
matching_service = MatchingService()

# Dependency to get services


def get_services():
    return {
        "image_service": image_service,
        "search_service": search_service,
        "matching_service": matching_service
    }


def normalize_and_hash_query(query: str) -> str:
    # Normalize the query: lowercase, remove extra whitespace
    normalized_query = ' '.join(query.lower().split())
    # Hash the normalized query
    return hashlib.md5(normalized_query.encode('utf-8')).hexdigest()


async def extract_matching_objects(self, matching_indices, search_results):
    extracted_objects = {}
    engines = ['amz', 'gs', 'gis', 'lens']

    for index, engine in zip(matching_indices, engines):
        print(f"Processing engine: {engine}, index: {index}")
        if engine == 'amz':
            results = self.cached_results.get(engine, {})
            if results:
                results = json.loads(results)
                results = results['results'][0]['content']['results']
                organic = results['results']['organic']
                amazon_choice = results['results']['amazons_choices']
                all_objects = organic + amazon_choice
                for item in all_objects:
                    if item.get('url_image') and item.get('pos') == index:
                        full_url = f"https://www.amazon.com{item.get('url')}"
                        extracted_objects['amazon'] = {
                            'title': item.get('title'),
                            'price': item.get('price'),
                            'link': full_url,
                            'image': item.get('url_image')
                        }
                        break
            else:
                print(f"No results found for engine {engine}")
        elif engine == 'gs':
            results = self.cached_results.get(engine, {})
            if 'organic_results' in results:
                for item in results['organic_results']:
                    if 'thumbnail' in item and item.get('position') == index:
                        extracted_objects['google_search'] = {
                            'title': item.get('title'),
                            'link': item.get('link'),
                            'image': item.get('thumbnail')
                        }
                        break
        elif engine == 'gis':
            results = self.cached_results.get(engine, {})
            if 'image_results' in results:
                for item in results['image_results']:
                    if 'thumbnail' in item and item.get('position') == index:
                        extracted_objects['google_image_search'] = {
                            'title': item.get('title'),
                            'link': item.get('link'),
                            'image': item.get('thumbnail')
                        }
                        break
        elif engine == 'lens':
            results = self.cached_results.get(engine, {})
            if 'visual_matches' in results:
                for item in results['visual_matches']:
                    if 'thumbnail' in item and item.get('position') == index:
                        extracted_objects['google_lens'] = {
                            'title': item.get('title'),
                            'link': item.get('link'),
                            'image': item.get('thumbnail')
                        }
                        break

    return extracted_objects


@app.post("/search", response_model=SearchResult)
async def reverse_search(
    image_url: Optional[str] = Query(
        None, description="URL of the image to search"),
    description: Optional[str] = Query(
        None, description="Optional description of the image"),
    image: Optional[UploadFile] = File(
        None, description="Image file to upload"),
    services: dict = Depends(get_services)
):
    if image_url is None and image is None:
        raise HTTPException(
            status_code=400, detail="Either image_url or image file must be provided")

    if image:
        # Convert uploaded image to URL using the image service
        image_url = await services["image_service"].upload_image(image)

    if image_url is None:
        raise HTTPException(
            status_code=500, detail="Failed to obtain image URL")

    # Generate cache key
    cache_key = f"search:{hashlib.md5(image_url.encode()).hexdigest()}"

    # Check if results are cached
    cached_result = redis_client.get(cache_key)
    if cached_result:
        return SearchResult(**json.loads(cached_result))

    try:
        # Get product query
        product_query_json = await services["image_service"].get_product_query(image_url)
        product_query_data = json.loads(product_query_json)
        query = product_query_data['query']

        # Perform searches
        amazon_result, google_result, gis_result, lens_result = await asyncio.gather(
            services["search_service"].amazon_search(query),
            services["search_service"].google_search(query),
            services["search_service"].google_image_search(image_url),
            services["search_service"].google_lens_search(image_url)
        )

        # Concatenate thumbnails
        image_bundle = await asyncio.gather(
            services["image_service"].concatenate_thumbnails(
                "amz", amazon_result, image_url),
            services["image_service"].concatenate_thumbnails(
                "gs", google_result, image_url),
            services["image_service"].concatenate_thumbnails(
                "gis", gis_result, image_url),
            services["image_service"].concatenate_thumbnails(
                "lens", lens_result, image_url)
        )

        # Get matching images
        matching_indices_json = await services["matching_service"].get_matching_images(image_bundle)
        matching_indices = json.loads(matching_indices_json)

        # Extract matching objects
        search_results = {
            "amz": amazon_result,
            "gs": google_result,
            "gis": gis_result,
            "lens": lens_result
        }
        matching_objects = await services["matching_service"].extract_matching_objects(
            list(matching_indices.values()), search_results
        )

        # Prepare final result
        final_result = {
            "query": query,
            "original_image": image_url,
            "matches": matching_objects
        }

        # Cache the results
        redis_client.setex(cache_key, 3600, json.dumps(
            final_result))  # Cache for 1 hour

        return SearchResult(**final_result)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process search: {str(e)}")
