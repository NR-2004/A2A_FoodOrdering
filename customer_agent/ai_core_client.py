import os, json, requests
from dotenv import load_dotenv
from ai_core_sdk.ai_core_v2_client import AICoreV2Client
from gen_ai_hub.proxy import GenAIHubProxyClient
from gen_ai_hub.proxy.native.openai import OpenAI

load_dotenv()

DESTINATION_NAME = os.getenv("DESTINATION_NAME")
RESOURCE_GROUP = os.getenv("RESOURCE_GROUP", "default")
SERVICE_KEY_PATH = os.getenv("DEST_SERVICE_KEY_PATH", "destination_service_key.json")


def load_destination_service_key(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def get_destination_config(destination_name: str) -> dict:
    dest_creds = load_destination_service_key(SERVICE_KEY_PATH)
    session = requests.Session()
    session.trust_env = False

    token_resp = session.post(
        f"{dest_creds['url']}/oauth/token",
        params={"grant_type": "client_credentials"},
        auth=(dest_creds["clientid"], dest_creds["clientsecret"]),
        timeout=15,
    )
    token_resp.raise_for_status()
    access_token = token_resp.json()["access_token"]

    dest_resp = session.get(
        f"{dest_creds['uri']}/destination-configuration/v1/destinations/{destination_name}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    dest_resp.raise_for_status()
    return dest_resp.json()["destinationConfiguration"]


def build_ai_core_client(destination_name: str = DESTINATION_NAME,
                          resource_group: str = RESOURCE_GROUP) -> AICoreV2Client:
    dest = get_destination_config(destination_name)
    base_url = dest["URL"].rstrip("/")
    if not base_url.endswith("/v2"):
        base_url += "/v2"
    return AICoreV2Client(
        base_url=base_url,
        auth_url=dest["tokenServiceURL"].rstrip("/") + "/oauth/token",
        client_id=dest["clientId"],
        client_secret=dest["clientSecret"],
        resource_group=resource_group,
    )


ai_core_client = build_ai_core_client()
proxy_client = GenAIHubProxyClient(ai_core_client=ai_core_client)

# Native OpenAI-compatible client. The deployment itself is selected by
# passing DEPLOYMENT_ID as `model` when creating a completion.
openai_client = OpenAI(proxy_client=proxy_client)
