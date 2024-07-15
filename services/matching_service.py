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
        message_text = (
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
