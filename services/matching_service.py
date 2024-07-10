from openai import AzureOpenAI
import json
from dotenv import load_dotenv
import os

class MatchingService:
    def __init__(self):
        self.azure_client = AzureOpenAI(
            api_key=os.getenv('AZURE_KEY'),
            api_version="2024-02-15-preview",
            azure_endpoint="https://buysmartusnc.openai.azure.com/"
        )

    async def get_matching_images(self, image_url):
        message_text = (
            "What is the product in the image? Specifically describe the product's apperance "
            "and identify its conspicuous features that makes it distinctive. According to its features, "
            "guess about the product's potential brands (but no larger than 3), and produce a search query "
            "preferrably with a product name to use on Amazon and Google and make sure you have the brands in your query as well. "
            "Return in JSON with potential brands, description, and query."
            )
        completion = self.azure_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": message_text},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                },
            ],
            max_tokens=2000,
            temperature=0,
            response_format={"type": "json_object"},
        )

        return completion.choices[0].message.content

    async def extract_matching_objects(self, matching_indices, search_results):
        # Implement the logic to extract matching objects from search results
        # This should be similar to your existing extract_matching_objects method
        pass