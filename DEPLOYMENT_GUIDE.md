# Deploy Leave Management System to Render

## Prerequisites
- GitHub repository with your code
- Render account (free tier available)
- PostgreSQL database connection string

## Step 1: Prepare Your Repository

1. **Push your code to GitHub** (if not already done):
   ```bash
   git add .
   git commit -m "Ready for Render deployment"
   git push origin main
   ```

2. **Ensure your repository contains**:
   - `render.yaml` (already created)
   - `Dockerfile` (already updated)
   - `requirements.txt`
   - `run.py`

## Step 2: Deploy to Render

1. **Sign up/login to Render** at [render.com](https://render.com)

2. **Create a new Web Service**:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select your leave-management-system repository
   - Render will automatically detect your `render.yaml` configuration

3. **Configure Environment Variables** (if not using render.yaml):
   - `FLASK_APP`: `run.py`
   - `FLASK_ENV`: `production`
   - `PORT`: `10000`
   - `POSTGRES_URI`: Your PostgreSQL connection string

## Step 3: Set Up Database

1. **Create PostgreSQL Database**:
   - In Render dashboard: "New +" → "PostgreSQL"
   - Choose free plan
   - Give it a name (e.g., `leave-management-db`)

2. **Get Connection String**:
   - Go to your database dashboard
   - Copy the "External Database URL"
   - Add this as `POSTGRES_URI` environment variable to your web service

## Step 4: Deploy and Test

1. **Automatic Deployment**:
   - Render will automatically build and deploy your application
   - Monitor the build logs for any errors

2. **Access Your Application**:
   - Once deployed, Render will provide a URL
   - Your app should be accessible at `https://your-app-name.onrender.com`

3. **Test Database Connection**:
   - Visit `https://your-app-name.onrender.com/db-check`
   - Should show "✅ Connected to PostgreSQL!"

## Troubleshooting

### Common Issues:

1. **Build Failures**:
   - Check Dockerfile syntax
   - Ensure all dependencies are in requirements.txt
   - Verify Python version compatibility

2. **Database Connection Errors**:
   - Verify POSTGRES_URI environment variable
   - Check if database is running
   - Ensure IP allowlist includes Render's network

3. **Application Not Starting**:
   - Check gunicorn command in Dockerfile
   - Verify PORT environment variable matches
   - Review application logs in Render dashboard

### Useful Commands:
```bash
# Test locally before deploying
docker build -t leave-app .
docker run -p 10000:10000 -e POSTGRES_URI="your_local_db_url" leave-app
```

## Post-Deployment

1. **Monitor Logs**: Use Render dashboard to monitor application logs
2. **Set Up Custom Domain**: Optional - add custom domain in Render settings
3. **Configure Backups**: Enable automatic backups for your PostgreSQL database
4. **Scale Up**: Upgrade plans if needed for production traffic

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `FLASK_APP` | Flask application entry point | `run.py` |
| `FLASK_ENV` | Flask environment | `production` |
| `PORT` | Application port | `10000` |
| `POSTGRES_URI` | Database connection string | `postgresql://user:pass@host:5432/dbname` |
| `SECRET_KEY` | Flask secret key | `your-secret-key-here` |

## Support

- Render documentation: [render.com/docs](https://render.com/docs)
- Flask deployment guide: [flask.palletsprojects.com](https://flask.palletsprojects.com/en/latest/deploying/)
