from serpapi import GoogleSearch
import aiohttp
from typing import Optional
from dotenv import load_dotenv
import os
import asyncio
from typing import Any

load_dotenv()

class SearchService:
    def __init__(self):
        self.url = "https://scraper-api.smartproxy.com/v2/scrape"
        self.google_key: Optional[str] = os.getenv('GOOGLE_API_KEY')
        self.serp_auth: Optional[str] = os.getenv('SERP_API_AUTH')

    async def amazon_search(self, query) -> str:
        payload = {
            "target": "amazon_search",
            "query": query,
            "page_from": "1",
            "parse": True
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": self.serp_auth
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, json=payload, headers=headers) as response:
                return await response.text()

    async def google_search(self, query: str):
        params = {
            "api_key": self.google_key,
            "engine": "google",
            "q": query,
            "location": "Austin, Texas, United States",
            "google_domain": "google.com",
            "gl": "us",
            "hl": "en"
        }
        search = GoogleSearch(params)
        results = await asyncio.to_thread(search.get_dict)
        return results

    async def google_image_search(self, image_url: str):
        params = {
            "api_key": self.google_key,
            "engine": "google_reverse_image",
            "google_domain": "google.com",
            "image_url": image_url
        }
        search = GoogleSearch(params)
        results = await asyncio.to_thread(search.get_dict)
        return results

    async def google_lens_search(self, image_url: str)-> dict[Any, Any]:
        params = {
            "api_key": self.google_key,
            "engine": "google_lens",
            "google_domain": "google.com",
            "url": image_url 
        }
        search = GoogleSearch(params)
        results = await asyncio.to_thread(search.get_dict)
        return results


# Example usage
async def main():
    search_service = SearchService()
    result = await search_service.google_lens_search("https://m.media-amazon.com/images/I/41H1NQVybjL.jpg")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())