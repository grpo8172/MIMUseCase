from __future__ import annotations

import os

from pydantic import BaseModel

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class GeminiClient:
    """Wrapper around Google Gen AI SDK in Vertex AI mode.

    This keeps the rest of the app independent from the SDK and makes it easier
    to mock the model in tests.
    """

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        project: str | None = None,
        location: str | None = None,
    ):
        self.model = model
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "australia-southeast1")

        if genai is None or types is None or not self.project:
            self.client = None
            return

        self.client = genai.Client(vertexai=True, project=self.project, location=self.location)

    @property
    def available(self) -> bool:
        return self.client is not None

    def generate_json(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        if not self.available:
            raise RuntimeError(
                "Gemini client is unavailable. Check dependencies and GOOGLE_CLOUD_PROJECT."
            )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2,
            ),
        )

        if getattr(response, "parsed", None) is not None:
            return response.parsed

        return schema.model_validate_json(response.text)
