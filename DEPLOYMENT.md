# NBA Transition Matrix Adjustments API - Render Deployment Guide

## 🚀 Overview

This guide will help you deploy the NBA Transition Matrix Adjustments API to Render, a cloud platform that makes it easy to deploy web services.

## 📋 Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Your code should be in a GitHub repository
3. **Database File**: The `nba_clean.db` file should be in the `backend/` directory

## 🏗️ Project Structure

```
markovbasketball/
├── backend/
│   ├── app/
│   │   ├── main.py              # Main FastAPI app
│   │   ├── simulation.py        # Markov simulation logic
│   │   └── transition_utils.py  # Transition adjustment functions
│   ├── requirements.txt         # Python dependencies
│   └── nba_clean.db            # NBA database (needs to be uploaded)
├── render.yaml                  # Render deployment configuration
└── DEPLOYMENT.md               # This file
```

## 🚀 Deployment Steps

### 1. Prepare Your Repository

Make sure your repository contains:
- ✅ All the Python files
- ✅ `requirements.txt` with dependencies
- ✅ `render.yaml` configuration
- ✅ `nba_clean.db` file in the `backend/` directory

### 2. Connect to Render

1. Go to [render.com](https://render.com) and sign in
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository
4. Select the repository containing this code

### 3. Configure the Service

Render will automatically detect the `render.yaml` file and configure:
- **Name**: `nba-transition-adjustments`
- **Environment**: Python
- **Build Command**: `pip install -r backend/requirements.txt`
- **Start Command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 4. Environment Variables

The service will automatically set:
- `PYTHON_VERSION`: 3.9.16
- `DB_PATH`: `/opt/render/project/src/backend/nba_clean.db`

### 5. Deploy

1. Click "Create Web Service"
2. Render will build and deploy your service
3. Wait for the build to complete (usually 2-5 minutes)

## 🌐 API Endpoints

Once deployed, your service will have these endpoints:

### Health Check
```
GET /health
```
Returns service status.

### Get Teams
```
GET /teams?season=2024-25
```
Returns list of available NBA teams.

### Generate Adjustments
```
POST /generate-adjustments
```
Generates transition matrix adjustments for a specific team.

**Request Body:**
```json
{
  "team": "LAC",
  "season": "2024-25",
  "adjustment_percentage": 5.0
}
```

**Response:** CSV file with transition matrix adjustments.

## 🧪 Testing Locally

Before deploying, test locally:

1. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Start the service:**
   ```bash
   uvicorn app.main:app --reload
   ```

3. **Run tests:**
   ```bash
   python test_api.py
   ```

## 🔧 Troubleshooting

### Common Issues

1. **Database not found:**
   - Ensure `nba_clean.db` is in the `backend/` directory
   - Check the `DB_PATH` environment variable

2. **Import errors:**
   - Verify all Python files are in the correct locations
   - Check that `requirements.txt` includes all dependencies

3. **Build failures:**
   - Check the build logs in Render
   - Ensure Python version compatibility

### Logs

View logs in Render:
1. Go to your service dashboard
2. Click "Logs" tab
3. Check for error messages

## 📊 Monitoring

Render provides:
- **Uptime monitoring**
- **Performance metrics**
- **Log aggregation**
- **Automatic scaling** (if configured)

## 🔄 Updates

To update your service:
1. Push changes to GitHub
2. Render automatically redeploys
3. Monitor the build logs

## 💰 Costs

- **Starter Plan**: $7/month (includes 750 hours)
- **Disk Storage**: $0.25/GB/month
- **Bandwidth**: Included in plan

## 🆘 Support

- **Render Documentation**: [docs.render.com](https://docs.render.com)
- **Render Support**: Available in the dashboard
- **GitHub Issues**: For code-related problems

## 🎯 Next Steps

After successful deployment:
1. Test all endpoints
2. Set up monitoring alerts
3. Configure custom domain (optional)
4. Set up CI/CD pipeline (optional)

---

**Happy Deploying! 🚀🏀**
