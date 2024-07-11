import aiohttp
import base64
from openai import AsyncAzureOpenAI
from search_service import SearchService
import cv2
import numpy as np
import json
import time
from dotenv import load_dotenv
import asyncio
import os
import matplotlib.pyplot as plt
import search_service

load_dotenv()

class ImageService:
    def __init__(self):
        # TODO 
        # s3 client
        self.azure_client = AsyncAzureOpenAI(
            api_key=os.getenv('AZURE_KEY'),
            api_version="2024-02-15-preview",
            azure_endpoint="https://buysmartusnc.openai.azure.com/"
        )
        self.IMGBB_API_KEY = os.getenv('IMGBB_API_KEY')

    async def upload_image(self, file_path):
        with open(file_path, 'rb') as file:
            file_content = base64.b64encode(file.read()).decode('utf-8')

        data = {
            'key': self.IMGBB_API_KEY,
            'image': file_content
        }

        async with aiohttp.ClientSession() as session:
            async with session.post('https://api.imgbb.com/1/upload', data=data) as response:
                result = await response.json()
                return result['data']['url']
    
    async def get_product_description(self, image_url: str):
        message_text = (
            "What is the product in the image? Specifically describe the product's apperance "
            "and identify its conspicuous features that makes it distinctive. According to its features, "
            "guess about the product's potential brands (but no larger than 3), and produce a search query "
            "preferrably with a product name to use on Amazon and Google and make sure you have the brands in your query as well. "
            "Return in JSON with potential brands, description, and query."
            )
        completion = await self.azure_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": message_text},
                {"role": "user", "content": [{"type": "image_url", "image_url": {"url": image_url}}]},
            ],
            max_tokens=2000,
            temperature=0,
            response_format={"type": "json_object"},
        )
        return completion.choices[0].message.content
    
    async def fetch_image(self, session, url):
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    print(f"Failed to fetch image from {url}: HTTP {response.status}")
                    return None
        except Exception as e:
            print(f"Error fetching image from {url}: {str(e)}")
            return None

    async def process_image(self, img_data, index):
        if img_data is None:
            # Return a placeholder image if fetch failed
            img = np.full((150, 150, 3), 200, dtype=np.uint8)
            cv2.putText(img, "Error", (30, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        else:
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                # Another placeholder for decoding errors
                img = np.full((150, 150, 3), 220, dtype=np.uint8)
                cv2.putText(img, "Decode Error", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            else:
                img = cv2.resize(img, (150, 150), interpolation=cv2.INTER_AREA)

        # Add white space for label
        img = cv2.copyMakeBorder(img, 0, 20, 0, 0, cv2.BORDER_CONSTANT, value=[255, 255, 255])
        
        # Add label
        cv2.putText(img, str(index), (75, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        
        return img
    
    async def concatenate_thumbnails(self, engine: str, search_results, image_url, columns=6):
        if engine == 'gs':
            thumbnails = [image_url] + [
                result['thumbnail']
                for result in search_results['organic_results']
                if 'thumbnail' in result
            ]

        elif engine == 'amz':
            data = json.loads(search_results)
            results = data['results'][0]['content']['results']
            organic = results['results']['organic']
            amazon_choice = results['results']['amazons_choices']
            o_imgs = [item['url_image'] for item in organic if 'url_image' in item]
            ac_imgs = [item['url_image'] for item in amazon_choice if 'url_image' in item]
            thumbnails = [image_url] + o_imgs + ac_imgs

        elif engine == 'gis':
            thumbnails = [image_url] + [
                result['thumbnail']
                for result in search_results['image_results']
                if 'thumbnail' in result
            ]

        elif engine == 'lens':
            thumbnails = [image_url] + [
                result['thumbnail']
                for result in search_results['visual_matches']
                if 'thumbnail' in result
            ]

        else:
            raise ValueError(f"Unknown engine: {engine}")

        thumbnails = thumbnails[:21]  # Limit to 21 images

        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_image(session, url) for url in thumbnails]
            img_data_list = await asyncio.gather(*tasks)

        process_tasks = [self.process_image(img_data, i) for i, img_data in enumerate(img_data_list)]
        images = await asyncio.gather(*process_tasks)

        rows = (len(images) + columns - 1) // columns
        grid = np.zeros((rows * 170, columns * 150, 3), dtype=np.uint8)

        for i, img in enumerate(images):
            row = i // columns
            col = i % columns
            grid[row*170:row*170+170, col*150:col*150+150] = img

        _, buffer = cv2.imencode('.jpg', grid, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        plt.imshow(cv2.cvtColor(grid, cv2.COLOR_BGR2RGB))
        plt.axis('off')
        plt.show()
        img_byte_arr = buffer.tobytes()


# Example usage
async def main():
    start = time.time()

    image_service = ImageService()
    search_service = SearchService()

    google_img_search = await search_service.google_search("owala")
    result = await image_service.concatenate_thumbnails("gs", google_img_search, "https://m.media-amazon.com/images/I/41H1NQVybjL.jpg")

    
    end = time.time()
    print(result)
    print(end - start)
    


if __name__ == "__main__":
    asyncio.run(main())