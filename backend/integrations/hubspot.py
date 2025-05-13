# hubspot.py

import os
import json
import secrets
import asyncio
import base64
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
from dotenv import load_dotenv
from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

# Load environment variables from .env file
load_dotenv()

# Access the variables using os.getenv
CLIENT_ID = os.getenv("HUBSPOT_CLIENT_ID")
CLIENT_SECRET = os.getenv("HUBSPOT_CLIENT_SECRET")
REDIRECT_URI = os.getenv("HUBSPOT_REDIRECT_URI")
authorization_url = f"https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"

encoded_client_id_secret = base64.b64encode(
    f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
).decode()

scope = "crm.objects.users.read crm.objects.contacts.write crm.objects.users.write oauth crm.objects.companies.write crm.objects.companies.read crm.objects.contacts.read"


async def authorize_hubspot(user_id, org_id):
    state_data = {
        "state": secrets.token_urlsafe(32),
        "user_id": user_id,
        "org_id": org_id,
    }
    encoded_state = json.dumps(state_data)
    await add_key_value_redis(
        f"hubspot_state:{org_id}:{user_id}", encoded_state, expire=600
    )

    return f"{authorization_url}&state={encoded_state}&scope={scope}"


async def oauth2callback_hubspot(request: Request):
    if request.query_params.get("error"):
        raise HTTPException(status_code=400, detail=request.query_params.get("error"))
    code = request.query_params.get("code")
    encoded_state = request.query_params.get("state")
    state_data = json.loads(encoded_state)

    original_state = state_data.get("state")
    user_id = state_data.get("user_id")
    org_id = state_data.get("org_id")

    saved_state = await get_value_redis(f"hubspot_state:{org_id}:{user_id}")

    if not saved_state or original_state != json.loads(saved_state).get("state"):
        raise HTTPException(status_code=400, detail="State does not match.")

    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                "https://api.hubapi.com/oauth/v1/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                },
                headers={
                    "Authorization": f"Basic {encoded_client_id_secret}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            ),
            delete_key_redis(f"hubspot_state:{org_id}:{user_id}"),
        )

    await add_key_value_redis(
        f"hubspot_credentials:{org_id}:{user_id}",
        json.dumps(response.json()),
        expire=600,
    )

    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)


async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f"hubspot_credentials:{org_id}:{user_id}")
    if not credentials:
        raise HTTPException(status_code=400, detail="No credentials found.")
    credentials = json.loads(credentials)
    if not credentials:
        raise HTTPException(status_code=400, detail="No credentials found.")
    await delete_key_redis(f"hubspot_credentials:{org_id}:{user_id}")

    return credentials


async def create_integration_item_metadata_object(
    response_json: str,
    key: str,
) -> IntegrationItem:
    """creates an integration metadata object from the response"""

    name = (
        f"{response_json['properties'].get('firstname')} {response_json['properties'].get('lastname')}"
        if key == "contacts"
        else response_json["properties"].get("name") if key == "companies" else None
    )
    parent_id = (
        response_json["properties"].get("email")
        if key == "contacts"
        else response_json["properties"].get("domain") if key == "companies" else None
    )
    integration_item_metadata = IntegrationItem(
        obj_id=response_json.get("id"),
        name=name,
        obj_type=key,
        parent_id=parent_id,
        creation_time=response_json["properties"].get("createdate"),
        last_modified_time=response_json.get("updatedAt"),
    )

    return integration_item_metadata


async def get_items_hubspot(credentials) -> list[IntegrationItem]:
    """Aggregates all metadata relevant for a hubspot integration"""
    try:
        credentials = json.loads(credentials)
        async with httpx.AsyncClient() as client:
            contacts = client.get(
                "https://api.hubapi.com/crm/v3/objects/contacts",
                headers={
                    "Authorization": f'Bearer {credentials.get("access_token")}',
                },
            )
            companies = client.get(
                "https://api.hubapi.com/crm/v3/objects/companies",
                headers={
                    "Authorization": f'Bearer {credentials.get("access_token")}',
                },
            )

            # Wait for all tasks to complete concurrently
            contacts_response = await contacts
            companies_response = await companies

            # Raise exception if the requests fail
            contacts_response.raise_for_status()
            companies_response.raise_for_status()
            response = {
                "results": {
                    "contacts": contacts_response.json()["results"],
                    "companies": companies_response.json().get("results"),
                }
            }

            if response:
                list_of_integration_item_metadata = []
                for key, result in response["results"].items():
                    for each in result:
                        metadata = await create_integration_item_metadata_object(
                            each, key
                        )
                        list_of_integration_item_metadata.append(metadata)

                print(list_of_integration_item_metadata)
            return list_of_integration_item_metadata
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
