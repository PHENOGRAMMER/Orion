# Deploy Orion on Google Cloud Run

This guide deploys the no-LLM Orion backend to Cloud Run. The Streamlit
frontend should be deployed separately on Streamlit Community Cloud.

## Important limitation

Cloud Run cannot read a user's local Windows path such as
`C:\Users\name\Repository`. The current path-based scanner can only read
files available inside the container. Before public users can scan arbitrary
local repositories, Orion needs a ZIP upload flow or a local scanner agent.

## 1. Prerequisites

Install and authenticate the Google Cloud CLI, then select a project:

```powershell
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

Set a deployment region, preferably close to the expected users:

```powershell
$env:GCP_REGION = "asia-south1"
$env:GCP_PROJECT = (gcloud config get-value project).Trim()

gcloud artifacts repositories create orion `
  --repository-format=docker `
  --location $env:GCP_REGION `
  --description "Orion container images"
```

## 2. Build and deploy the backend

Run these commands from the Orion repository root. Cloud Build uses the root
context because the Dockerfile copies `backend/` and `frontend/`.

```powershell
gcloud builds submit --tag "${env:GCP_REGION}-docker.pkg.dev/${env:GCP_PROJECT}/orion/orion-api" .

gcloud run deploy orion-api `
  --image "${env:GCP_REGION}-docker.pkg.dev/${env:GCP_PROJECT}/orion/orion-api" `
  --region $env:GCP_REGION `
  --platform managed `
  --allow-unauthenticated `
  --port 8080 `
  --memory 2Gi `
  --cpu 2 `
  --min-instances 0 `
  --max-instances 1 `
  --set-env-vars "AUTH_ENABLED=true,AUTH0_ENABLED=true,ORION_LLM_ENABLED=false,PROJECT_ROOT=/workspace,ALLOWED_ROOTS=/workspace,ALLOW_UNSAFE_SCAN_PATHS=false,PERSISTENCE_DB=/tmp/orion.db,ALLOW_ORIGINS=https://YOUR_STREAMLIT_APP.streamlit.app"
```

The command returns the backend URL. Save it for the Streamlit configuration.

## 3. Configure secrets

Do not put these values in Git or in this document. Use Secret Manager or set
them through the Cloud Run console:

- `ADMIN_API_KEY`
- `AUTH0_ISSUER_BASE_URL`
- `AUTH0_AUDIENCE`
- `ORION_IDENTITY_BRIDGE_SECRET`

The bridge secret must match the `[orion] identity_bridge_secret` value in the
Streamlit app's secrets.

For an initial test, the Cloud Run console can add these variables under
**Edit and deploy new revision → Variables & Secrets**. Secret Manager is the
preferred option once the deployment is working.

## 4. Configure Streamlit Community Cloud

Deploy `frontend/streamlit_app.py` and set these environment variables/secrets:

```text
ORION_API_URL=https://YOUR_CLOUD_RUN_URL
ORION_LLM_ENABLED=false
```

Keep the existing Auth0 OIDC values in Streamlit secrets and update Auth0 with
the Streamlit Community Cloud callback and logout URLs.

## 5. Verify the backend

```powershell
Invoke-RestMethod "https://YOUR_CLOUD_RUN_URL/health"
Invoke-RestMethod "https://YOUR_CLOUD_RUN_URL/llm/health"
```

The LLM health response should contain:

```json
{
  "enabled": false,
  "model_loaded": false
}
```

Cloud Run's local filesystem is ephemeral. `/tmp/orion.db` is suitable for a
first smoke test, but persistent multi-week scan history requires an external
database such as PostgreSQL.
