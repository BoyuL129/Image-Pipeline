from openai import AsyncAzureOpenAI
import json
from dotenv import load_dotenv
import os

class MatchingService:
    def __init__(self):
        self.azure_client = AsyncAzureOpenAI(
            api_key=os.getenv('AZURE_KEY'),
            api_version="2024-02-15-preview",
            azure_endpoint="https://buysmartusnc.openai.azure.com/"
        )

    async def get_matching_images(self, image_urls: list[str]):
        message_text= (
        "You will be given four image galleries with each image labeled from 0 to n. "
        "Combine with the description and compare all other images to image 0 and return in JSON "
        "with the image index that is visually matching closest with image 0 for each image gallery")
        completion = await self.azure_client.chat.completions.create(
        model="gpt-4o",
        messages=[
        {"role": "system", "content": message_text},
        {
        "role": "user",
        "content": [
            # {
            # "type": "text",
            # # "text": "User description: " + self.description,
            # },
            {
            "type": "image_url",
            "image_url": {
                "url": image_urls[0],
            },
            },
            {
            "type": "image_url",
            "image_url": {
                "url": image_urls[1],
            },
            },
            {
            "type": "image_url",
            "image_url": {
                "url": image_urls[2],
            },
            },
            {
            "type": "image_url",
            "image_url": {
                "url": image_urls[3],
            },
            },
        ],
        }
    ],
        max_tokens=2000,
        temperature=0,
        response_format={"type": "json_object"},
    )

        return completion.choices[0].message.content

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