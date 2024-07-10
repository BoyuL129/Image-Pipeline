import aiohttp
import base64
from openai import AsyncAzureOpenAI
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from dotenv import load_dotenv
import os

load_dotenv()

class ImageService:
    def __init__(self):
        self.azure_client = AsyncAzureOpenAI(
            api_key=os.getenv('AZURE_KEY'),
            api_version="2024-02-15-preview",
            azure_endpoint="https://buysmartusnc.openai.azure.com/"
        )
        self.IMGBB_API_KEY = os.getenv('IMGBB_API_KEY')

    async def process_image(self, image_input):
        if image_input.startswith(('http://', 'https://')):
            return image_input
        return await self.upload_image(image_input)

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

    async def get_product_description(self, image_url):
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

    async def concatenate_thumbnails(self, engine, search_results, columns=6, output_path=None):
        if output_path is None:
            output_path = "thumbnails_" + engine + ".jpg"

        if engine == 'gs':
            thumbnails = [self.image_url] + [
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
            thumbnails = [self.image_url] + o_imgs + ac_imgs

        elif engine == 'gis':
            thumbnails = [self.image_url] + [
                result['thumbnail']
                for result in search_results['image_results']
                if 'thumbnail' in result
            ]

        elif engine == 'lens':
            thumbnails = [self.image_url] + [
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