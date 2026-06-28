## Intro

This a notepad to record my notes as working on this project (since it is for an interview it is being committed).

## Setup

Some notes about setting up the project, issues I had and how they were fixed.

### Notes (Non critical)

1. Venv needs postgres dev headers to install for pyscopg install (not mentioned in setup)
2. Base TLS for redis sets no cert verification, and was never overridden for production. This may or may not be an issue depending on how redis is deployed. If using publically accessible redis instance (ie. hosted) it probably should use a trusted TLS cert and set CERT_REQUIRED. If it is self hosted as it seems to be from the production docker compose it might be ok since it is running on the same host.
3. In general production config seems incomplete (missing configs such as EMAIL_HOST, probably others). This is not production so I am leaving it for now but still taking note.

### Improvements

1. Added docker compose ps to justfile to monitor status of containers for convenience.
2. Added docker compose restart to justfile to restart individual services.

### Issues (Critical or require fixes)

1. Missing dockerfile for local postgres. Docker compose points to compose/production/postgres in docker-compose.local.yml. Replaced with a stock image from docker hub. I am not sure why a custom image is needed, if there is additional setup that causes issues I will find out later.
2. Dockerfile references production entrypoint. Fixed by creating a entrypoint that just passes the command (Will see how that works)
3. Settings assumes a DATABASE_URL env variable, while docker compose passes in the the DB config as separate parameters. Two options either change the DB config in Base settings to load from separate components or pass the DATABASE_URL as a new environment variable. I went with the later and configuring it in the local django dotenv file. This more clearly separates the DB config for the app from the DB config of the postgres docker container and would make it easier to for example switch to an external DB provider. The downside is as it currently is defined DB config is duplicated and would not likely change, so updates to the connection will have to be done in both places.
4. Swagger UI had inconsistent behavior for the User (and later presumably Study) API endpoints. I added COMPONENT_SPLIT to spectacular settings to properly generate the Auth Token from swagger and reordered the DRF auth methods so that specifying the API token in the swagger UI authenticates the correct user (instead of always using the cookie that has to be set to access the page).

### Future Improvements

1. Dockerfile builds could be optimized using multistage builds
