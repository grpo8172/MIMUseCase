from google import genai
from google.genai import types
from vertexai.agent_engines import AdkApp

from app.adk_agent.agent import root_agent

client = genai.Client(
    vertexai=True,
    project="project-8ecd61cd-68ba-43c2-abd",
    location="australia-southeast1",
)

app = AdkApp(agent=root_agent)

remote_agent = client.agent_engines.create(
    agent=app,
    config={
        "requirements": [
            "google-cloud-aiplatform[agent_engines,adk]",
            "mcp",
            "httpx",
        ],
        "staging_bucket": "gs://YOUR-STAGING-BUCKET",
        "identity_type": types.IdentityType.AGENT_IDENTITY,
    },
)

print(remote_agent.api_resource.name)
