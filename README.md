# Spotify AI Chat Agent

A FastAPI-based AI chat agent that integrates with Spotify's API to provide intelligent music recommendations and insights. This application uses LangChain agents powered by OpenAI's GPT models to interact with users about their Spotify data in natural language.


## 🛠️ Technologies Used

- **Backend Framework**: FastAPI (Python web framework)
- **AI/ML**: 
  - LangChain (agent framework)
  - OpenAI GPT models (language model)
- **Authentication**: 
  - JWT tokens (session management)
  - Spotify OAuth 2.0 (music data access)
- **Database**: Google Cloud Firestore (session storage)
- **Music API**: Spotify Web API via Spotipy
- **Deployment**: Google Cloud Run (containerized deployment)

## 📋 Prerequisites

- Python 3.8+
- Google Cloud Project with Firestore enabled
- Spotify Developer Account
- OpenAI API Key

## 🚀 Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Spotify App Setup

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Note your `Client ID` and `Client Secret`
4. Set your redirect URI (e.g., `http://localhost:8080/spotify/callback` for local development)

### 4. Google Cloud Setup

1. Create a Google Cloud Project
2. Enable the Firestore API
3. Set up authentication (Application Default Credentials or Service Account)

### 5. Environment Variables

Create a `.env` file or set the following environment variables:

```bash
# Required - JWT Secret Key
SECRET_KEY=your-secret-key-here

# Required - Spotify OAuth Configuration
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
SPOTIFY_REDIRECT_URI=http://localhost:8080/spotify/callback

# Required - OpenAI API Key for LangChain
OPENAI_API_KEY=your-openai-api-key

# Required for Google Cloud deployment
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=your-firestore-location

# Optional - Google Cloud credentials (if not using default)
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
```

### 6. Run the Application

```bash
python main.py
```

The application will start on `http://localhost:8080`


## 💬 Usage Flow

1. **Get Authentication**: Visit `/spotify/login` to get your JWT token and Spotify auth URL
2. **Complete OAuth**: Visit the returned auth URL to authorize Spotify access
3. **Start Chatting**: Use the JWT token to make requests to `/chat` endpoint

Example chat request:
```bash
curl -X POST "http://localhost:8080/chat" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are my top 5 favorite songs?"}'
```

## ☁️ Google Cloud Deployment

Deploy to Google Cloud Run with a single command:

```bash
gcloud run deploy spotify-agent-service \
  --source . \
  --region us-west1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION,SECRET_KEY=$SECRET_KEY,SPOTIFY_CLIENT_ID=$SPOTIFY_CLIENT_ID,SPOTIFY_CLIENT_SECRET=$SPOTIFY_CLIENT_SECRET,SPOTIFY_REDIRECT_URI=$SPOTIFY_REDIRECT_URI,OPENAI_API_KEY=$OPENAI_API_KEY
```

Make sure to update your `SPOTIFY_REDIRECT_URI` to match your deployed service URL:
```
SPOTIFY_REDIRECT_URI=https://your-service-url/spotify/callback
```
