# Simple Firebase Deployment (No gcloud Required)

This guide deploys your Academy Dashboard to Firebase **without installing Google Cloud SDK**.

## Recommended Approach: Firebase Hosting + Render Backend

I recommend this hybrid approach as it's the simplest:

### Step 1: Deploy Flask Backend to Render.com

1. **Go to [render.com](https://render.com)** and sign up with GitHub
2. **Connect your GitHub repository** (or push your code to GitHub first)
3. **Create a new "Web Service":**
   - Select your repository
   - Runtime: Python
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`
   - Environment: Free tier (or Starter for better performance)
4. **Click Deploy**
5. **Get your backend URL:** Copy the URL from Render (e.g., `https://academy-dashboard.onrender.com`)

### Step 2: Deploy Frontend to Firebase Hosting

1. **Create a `public/` directory in your project root:**
   ```powershell
   mkdir public
   copy templates\dashboard.html public\index.html
   copy static\*.css public\
   copy static\*.js public\
   ```

2. **Create `public/config.js` with your backend URL:**
   ```javascript
   // public/config.js
   const API_BASE_URL = "https://academy-dashboard.onrender.com";
   ```

3. **Update your frontend to use this config** (in any JavaScript files that make API calls):
   ```javascript
   // Example: Instead of fetch('/api/centers')
   // Use: fetch(API_BASE_URL + '/api/centers')
   ```

4. **Deploy to Firebase Hosting:**
   ```powershell
   firebase deploy --only hosting
   ```

5. **Get your Firebase Hosting URL** from the console output

## Alternative: Firebase Cloud Run (No Local Setup)

If you prefer everything in Firebase:

1. **Go to [Firebase Console](https://console.firebase.google.com/)**
2. **Select your `hrishi-dashboard` project**
3. **Go to Build → Cloud Run**
4. **Click "Create Service"**
5. **Upload your Dockerfile:**
   - Copy content from your local Dockerfile
   - Set memory to 512MB
   - Set CPU to 1
   - Click Deploy

6. **Get your Cloud Run URL**
7. **Configure environment variables in the Cloud Run console:**
   - `PRODUCTION=true`
   - `SECRET_KEY=<your-random-key>`

## Setting Environment Variables in SQLite Apps

Since you're using SQLite (local database), your data will be stored in the container but lost on restart. For production:

1. **Use Cloud Firestore instead:** Migrate your data to Firebase's Firestore database (recommended for serverless)
2. **Or use Cloud SQL:** PostgreSQL database hosted on Google Cloud (see FIREBASE_DEPLOYMENT_GUIDE.md for details)

## Testing Your Deployment

```powershell
# Test the deployed backend
Invoke-WebRequest "https://your-render-url.onrender.com/dashboard"

# Test Firebase Hosting
# Visit https://hrishi-dashboard.web.app in your browser
```

## Update Code After Deployment

### For Backend (Render):
```powershell
git add .
git commit -m "Updated code"
git push
# Render auto-deploys on git push!
```

### For Frontend (Firebase):
```powershell
firebase deploy --only hosting
```

## Troubleshooting

**Backend won't deploy on Render?**
- Check that requirements.txt has all dependencies
- Verify Dockerfile works locally: `docker build -t test . && docker run -p 8080:8080 test`

**Firebase hosting shows blank page?**
- Check browser console for JavaScript errors
- Verify API_BASE_URL is correct in config.js
- Check CORS settings on your backend

**Database errors?**
- If using SQLite: data resets on container restart (use Firestore or Cloud SQL)
- Check database connection in app.py

## Cost Estimate (Monthly):

- **Firebase Hosting:** Free tier (with paid options)
- **Render Backend:** Free tier (sleeps after 15 min inactivity; $7/mo paid tier)
- **Total:** Free or ~$7/month

## Next Steps

1. Create GitHub repo if you haven't
2. Deploy backend to Render (5 min)
3. Create `public/` folder with static files
4. Deploy frontend to Firebase Hosting (2 min)
5. Test both work together
6. Set up custom domain (optional)

## Useful Links

- [Render.com Documentation](https://render.com/docs)
- [Firebase Hosting Docs](https://firebase.google.com/docs/hosting)
- [Firebase Console](https://console.firebase.google.com/)
