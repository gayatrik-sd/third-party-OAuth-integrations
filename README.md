# 🛠️ OAuth Integration Project

This project demonstrates how to integrate with multiple third-party applications using **OAuth 2.0** and consume their **API metadata**. The applications integrated in this project are:

- **Hubspot**
- **Airtable**
- **Notion**

---

## 📌 Features

- Secure OAuth 2.0 authorization flow with token management
- API integration with multiple third-party services
- Retrieval and processing of metadata from each service
- Unified interface for interacting with connected services

---

## 🚀 Getting Started

### Prerequisites

- Python (FastAPI)
- React
- A `.env` file configured with the following credentials:

```env
NOTION_CLIENT_ID=19ed872b-594c-80f2-acbc-0037c92a1d0a
NOTION_CLIENT_SECRET="your_secret"
NOTION_REDIRECT_URI=http://localhost:8000/integrations/notion/oauth2callback
AIRTABLE_CLIENT_ID=329147ef-ac8b-4863-bced-77b7b195258f
AIRTABLE_CLIENT_SECRET="your_secret"
AIRTABLE_REDIRECT_URI=http://localhost:8000/integrations/airtable/oauth2callback
HUBSPOT_CLIENT_ID=59c6a8cd-50e7-4d11-a61d-1c8d95cbc26c
HUBSPOT_CLIENT_SECRET="your_secret"
HUBSPOT_REDIRECT_URI=http://localhost:8000/integrations/hubspot/oauth2callback
```

### 🔑 OAuth Flow

Each third-party app uses the OAuth 2.0 Authorization Code Grant flow:

- User is redirected to the app’s OAuth consent screen
- After authorization, the app redirects back with a code
- The server exchanges the code for an access token
- The access token is used to fetch metadata from the app's API

### 🧪 Running Locally

```bash
git clone https://github.com/yourusername/oauth-integration-project.git
cd frontend
npm i
npm run start
cd ../backend
uvicorn main:app —reload // in your venv
```


