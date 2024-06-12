import requests
from openai import AzureOpenAI
from serpapi import GoogleSearch
import base64
import json
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import math
import concurrent.futures
import threading

class ImageSearchPipeline:
    def __init__(self, image_url, description=None):
        self.image_url = image_url
        self.description = description

    def get_product_description(self):
        message_text = (
            "What is the product in the image? Specifically describe the product's apperance "
            "and identify its conspicuous features that makes it distinctive. According to its features, "
            "guess about the product's potential brands (but no larger than 3), and produce a search query "
            "preferrably with a product name to use on Amazon and Google and make sure you have the brands in your query as well. "
            "Return in JSON with potential brands, description, and query."
        )
        azure_client_westus3 = AzureOpenAI(
            api_key="66cfcde63be3491f82c764c4cff7b6d5",
            api_version="2024-02-15-preview",
            azure_endpoint="https://buysmartusnc.openai.azure.com/"
        )
        completion = azure_client_westus3.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": message_text},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": self.image_url},
                        },
                    ],
                },
            ],
            max_tokens=2000,
            temperature=0,
            response_format={"type": "json_object"},
        )

        return completion.choices[0].message.content

    def google_image_search(self, image):
        params = {
            "api_key": "ae041daff797b75cd1cc83d15bc09ef8853c296ca38b13e19872c9914014aaf4",
            "engine": "google_reverse_image",
            "google_domain": "google.com",
            "image_url": image
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        return results

    def google_lens_search(self, image):
        params = {
            "api_key": "ae041daff797b75cd1cc83d15bc09ef8853c296ca38b13e19872c9914014aaf4",
            "engine": "google_lens",
            "google_domain": "google.com",
            "url": image
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        return results

    def amazon_search(self, query):
        url = "https://scraper-api.smartproxy.com/v2/scrape"

        payload = {
            "target": "amazon_search",
            "query": query,
            "page_from": "1",
            "parse": True
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": "Basic VTAwMDAxMjk0MjQ6UmthN3VzOU8zcW1qNWd1Vkhj"
        }

        response = requests.post(url, json=payload, headers=headers)

        return response.text

    def google_search(self, query):
        params = {
            "api_key": "ae041daff797b75cd1cc83d15bc09ef8853c296ca38b13e19872c9914014aaf4",
            "engine": "google",
            "q": query,
            "location": "Austin, Texas, United States",
            "google_domain": "google.com",
            "gl": "us",
            "hl": "en"
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        return results

    def upload_image(self, file_path):
        IMGBB_API_KEY = 'bda9a97df6dc7355566874d7730b8100'
        with open(file_path, 'rb') as file:
            file_content = base64.b64encode(file.read()).decode('utf-8')

        data = {
            'key': IMGBB_API_KEY,
            'image': file_content
        }

        response = requests.post('https://api.imgbb.com/1/upload', data=data)
        return response.json()['data']['url']

    def concatenate_thumbnails(self, initial_image_url, engine, search_results, columns=6, output_path=None):
        if output_path is None:
            output_path = "thumbnails_" + engine + ".jpg"

        if engine == 'gs':
            thumbnails = [initial_image_url] + [
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
            thumbnails = [initial_image_url] + o_imgs + ac_imgs

        elif engine == 'gis':
            thumbnails = [initial_image_url] + [
                result['thumbnail']
                for result in search_results['image_results']
                if 'thumbnail' in result
            ]

        elif engine == 'lens':
            thumbnails = [initial_image_url] + [
                result['thumbnail']
                for result in search_results['visual_matches']
                if 'thumbnail' in result
            ]

        thumbnails = thumbnails[:21]

        images = []
        for index, url in enumerate(thumbnails):
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
            img = img.resize((150, 150))
            label_img = Image.new('RGB', (img.width, img.height + 20), (255, 255, 255))
            label_img.paste(img, (0, 0))

            draw = ImageDraw.Draw(label_img)
            font = ImageFont.load_default()
            text = f"{index}"
            text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
            draw.text(((label_img.width - text_width) // 2, img.height + 2), text, fill="black", font=font)

            images.append(label_img)

        rows = math.ceil(len(images) / columns)
        total_width = columns * images[0].width
        total_height = rows * images[0].height

        concatenated_img = Image.new('RGB', (total_width, total_height))

        x_offset = 0
        y_offset = 0
        for i, img in enumerate(images):
            concatenated_img.paste(img, (x_offset, y_offset))
            x_offset += img.width
            if (i + 1) % columns == 0:
                x_offset = 0
                y_offset += img.height

        concatenated_img.save(output_path)
        return output_path

    
