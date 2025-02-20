# Variables
PROJECT_ID=orderflow-451220
REPO=my-repo
APP_NAME=my-app
SERVICE_NAME=orderflow-app
REGION=us-central1
IMAGE=us-central1-docker.pkg.dev/$(PROJECT_ID)/$(REPO)/$(APP_NAME)

# Build the Docker image for AMD64
build:
	docker build --platform=linux/amd64 -t $(IMAGE) .

# Push the image to Google Artifact Registry
push: build
	docker push $(IMAGE)

# Deploy to Google Cloud Run
deploy: push
	gcloud run deploy $(SERVICE_NAME) \
	  --image=$(IMAGE) \
	  --region=$(REGION) \
	  --allow-unauthenticated