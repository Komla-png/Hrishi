# Firebase Deployment Guide for Academy Dashboard

This guide walks you through deploying the Academy Dashboard Flask application to Firebase Cloud Run.

## Prerequisites

1. **Google Account**: You need a Google account with Firebase enabled
2. **Firebase CLI**: Install with `npm install -g firebase-tools` (already done based on terminal history)
3. **Google Cloud SDK**: Install from https://cloud.google.com/sdk/docs/install
4. **Project Structure**: Already configured with Docker and Cloud Build setup

## Step 1: Create a Firebase Project

1. Visit [Firebase Console](https://console.firebase.google.com/)
2. Click "Add Project"
3. Enter your project name (e.g., "academy-dashboard")
4. Choose your region and click "Create Project"
5. Wait for the project to be created

## Step 2: Set Up Google Cloud Project

After Firebase project is created, you'll need to set up Google Cloud:

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Select your Firebase project
3. Enable these APIs:
   - Cloud Run API
   - Cloud Build API
   - Container Registry API
   - Cloud Logging API

To enable APIs via CLI:
```powershell
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable logging.googleapis.com
```

## Step 3: Update Firebase Configuration

1. Edit `.firebaserc` and replace `YOUR_PROJECT_ID` with your actual Firebase project ID:

```json
{
  "projects": {
    "default": "your-project-id"
  }
}
```

To find your project ID, run:
```powershell
firebase list
```

## Step 4: Configure Environment Variables

Before deployment, set up environment variables in Cloud Run:

1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. After deploying (see step 5), click on your service
3. Click "Edit and Re-deploy"
4. Scroll to "Environment variables"
5. Add these variables:
   ```
   PRODUCTION=true
   SECRET_KEY=<generate-a-random-secret-key>
   ```
   
   To generate a random SECRET_KEY:
   ```powershell
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

## Step 5: Deploy to Cloud Run

### Option A: Automatic Deployment with Firebase CLI (Recommended)

```powershell
# Login to Firebase
firebase login

# Deploy
firebase deploy
```

### Option B: Manual Deployment with gcloud

```powershell
# Set your PROJECT_ID
$PROJECT_ID = "your-project-id"

# Build and push the Docker image
gcloud builds submit --tag gcr.io/$PROJECT_ID/academy-dashboard

# Deploy to Cloud Run
gcloud run deploy academy-dashboard `
  --image gcr.io/$PROJECT_ID/academy-dashboard `
  --platform managed `
  --region us-central1 `
  --allow-unauthenticated `
  --set-env-vars "PRODUCTION=true,SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')"
```

## Step 6: Set Up Database

### For SQLite (Simple, but single-instance only):
- Default: Flask app uses SQLite database stored in `instance/academy.db`
- Container restarts will preserve data if using Cloud Run's persistent storage

### For Production (Cloud SQL - Recommended):

1. Create a Cloud SQL PostgreSQL instance:
```powershell
gcloud sql instances create academy-db `
  --database-version POSTGRES_15 `
  --tier db-f1-micro `
  --region us-central1
```

2. Create database:
```powershell
gcloud sql databases create academy --instance=academy-db
```

3. Create database user:
```powershell
gcloud sql users create academy-user --instance=academy-db --password=YOUR_STRONG_PASSWORD
```

4. Update `requirements.txt` to include PostgreSQL connector:
```
psycopg2-binary==2.9.6
```

5. Update your Flask app to use Cloud SQL by setting these environment variables:
```
DATABASE_URL=postgresql://academy-user:PASSWORD@INSTANCE_IP/academy
```

## Step 7: Configure Custom Domain (Optional)

1. In Firebase Console, go to Hosting
2. Click "Add custom domain"
3. Follow the domain verification steps
4. Update DNS records as instructed

## Step 8: Monitor Your Deployment

### View Logs:
```powershell
gcloud run logs read academy-dashboard --limit 50
```

### Check Service Status:
```powershell
gcloud run services list
```

### View Real-time Logs:
```powershell
gcloud run logs read academy-dashboard --limit 50 --follow
```

## Troubleshooting

### Service won't start?
- Check logs: `gcloud run logs read academy-dashboard --limit 100`
- Verify environment variables are set
- Ensure health check passes (see Dockerfile HEALTHCHECK)

### Database errors?
- Confirm database connection string is correct
- Check Cloud SQL instance is running: `gcloud sql instances list`
- Verify firewall rules allow connection

### Memory/CPU issues?
- Increase Cloud Run resources in the console
- Optimize database queries
- Use caching where possible

## Deployment Costs

- **Cloud Run**: Pay per request (generous free tier: 2M requests/month)
- **Cloud Build**: 120 build-minutes/day free
- **Container Registry**: 0.5 GB free storage
- **Cloud SQL**: From $3.50/month for micro instance (if used)

## Redeploy After Code Changes

```powershell
# Commit your changes to git
git add .
git commit -m "Updated code"
git push

# Redeploy
firebase deploy
# or
gcloud run deploy academy-dashboard --source .
```

## Local Testing Before Deployment

```powershell
# Build and run Docker image locally
docker build -t academy-dashboard .
docker run -p 8080:8080 academy-dashboard
```

Then visit: http://localhost:8080

## Additional Resources

- [Firebase Documentation](https://firebase.google.com/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/latest/deploying/)

## Next Steps

1. Create the Firebase project
2. Update `.firebaserc` with your project ID
3. Run `firebase login`
4. Deploy with `firebase deploy`
5. Set up database and environment variables
6. Test the deployed application
7. Set up monitoring and error tracking
