from urllib.parse import urlencode
from fastapi import FastAPI, HTTPException, Depends, status, Query
import uuid
import os
import requests
import base64

from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from models import ChatRequest
from auth import verify_jwt_token, generate_jwt_and_store_session, store_spotify_tokens, get_spotify_tokens
from spotify_tools import create_spotify_tools


app = FastAPI(title="Simple Chat API", description="FastAPI with JWT Authentication")


@app.get("/spotify/callback")
async def spotify_callback(
    code: str = Query(None, description="Authorization code from Spotify"),
    error: str = Query(None, description="Error message from Spotify"),
    state: str = Query(None, description="State parameter for CSRF protection")
):
    """
    Spotify OAuth callback endpoint
    Spotify will redirect here with either a 'code' parameter (success) or 'error' parameter (failure)
    """
    print("Received spotify callback:")
    print(f"Code: {code}")
    print(f"Error: {error}")
    print(f"State: {state}")
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Spotify OAuth error: {error}"
        )
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No authorization code received"
        )
    
    # Extract session_id from state parameter
    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing state parameter"
        )
    
    try:
        # State format is "session_id:random_uuid"
        session_id, _ = state.split(":", 1)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter format"
        )
    
    # Exchange code for access token
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
    
    # Create basic auth header
    auth_str = f"{client_id}:{client_secret}"
    auth_bytes = auth_str.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
    # Prepare token request
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri
    }
        
    headers = {
        'Authorization': f'Basic {auth_b64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
        
    # Make the token exchange request
    response = requests.post(
        'https://accounts.spotify.com/api/token',
        data=token_data,
        headers=headers
    )
        
    if response.status_code != 200:
        print(f"Token exchange failed: {response.status_code}")
        print(f"Response: {response.text}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange code for token: {response.text}"
        )
        
    token_response = response.json()
    
    # Extract token information
    access_token = token_response.get('access_token')
    refresh_token = token_response.get('refresh_token')
    expires_in = token_response.get('expires_in')  # seconds
    token_type = token_response.get('token_type')
    scope = token_response.get('scope')
        
    print(f"Successfully obtained access token. Expires in: {expires_in} seconds")
    
    # Store tokens in the user's session
    try:
        store_spotify_tokens(session_id, access_token, refresh_token, expires_in, scope)
        print(f"Spotify tokens stored for session: {session_id}")
    except Exception as e:
        print(f"Failed to store Spotify tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store Spotify tokens"
        )
    
    return {
        "status": "success",
        "message": "Spotify authentication completed! You can now use your JWT token to make API calls.",
    }

@app.post("/chat")
async def chat_endpoint(chat_request: ChatRequest, current_user: dict = Depends(verify_jwt_token)):
    """
    Chat endpoint that uses a LangChain agent with Spotify tools
    """
    session_id = current_user.get("session_id")
    
    # Check if user has completed Spotify OAuth
    spotify_tokens = get_spotify_tokens(session_id)
    
    if not spotify_tokens:
        return {
            "message": "Complete Spotify authentication first by visiting /spotify/login",
            "received_message": chat_request.message,
            "spotify_authenticated": False
        }
    
    try:
        # Create Spotify tools with the user's access token
        spotify_tools = create_spotify_tools(spotify_tokens['access_token'])
        
        # Initialize the LLM (you'll need to set OPENAI_API_KEY environment variable)
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        
        # Create the agent prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant that can access a user's Spotify data. 
            You can help users explore their music, find songs, analyze their listening habits, and more.
            Always be conversational and helpful. When you use tools, explain what you're doing.
            
            Available tools allow you to:
            - Get user profile information
            - Get user's playlists
            - Get saved/liked tracks
            - Search for music
            - Get top tracks
            - Get recently played tracks
            
            Respond naturally and helpfully to the user's request."""),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create the agent
        agent = create_openai_functions_agent(llm, spotify_tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=spotify_tools, verbose=True)
        
        # Run the agent
        result = agent_executor.invoke({"input": chat_request.message})
        
        return {
            "message": result["output"],
            "received_message": chat_request.message,
            "spotify_authenticated": True
        }
        
    except Exception as e:
        print(f"Error in agent execution: {e}")
        return {
            "message": f"Sorry, I encountered an error: {str(e)}",
            "received_message": chat_request.message,
            "spotify_authenticated": True,
            "error": str(e)
        }

@app.get("/spotify/login")
async def spotify_login():
    """
    Initiate Spotify OAuth - this is the only way users authenticate
    Creates a session immediately and returns both the auth URL and JWT token
    """
    # Generate a new session immediately
    session_id = str(uuid.uuid4())
    
    # Generate JWT token for this session
    token = generate_jwt_and_store_session(session_id)
    
    # Generate a random state parameter that includes the session_id for CSRF protection
    # We'll use this to know which session to update after OAuth
    state = f"{session_id}:{str(uuid.uuid4())}"
    
    scope = 'user-read-private user-read-email user-top-read user-library-read user-follow-read playlist-read-private playlist-read-collaborative user-read-recently-played playlist-modify-public playlist-modify-private'
    params = {
        'response_type': 'code',
        'redirect_uri': os.getenv("SPOTIFY_REDIRECT_URI"),
        'client_id': os.getenv("SPOTIFY_CLIENT_ID"),
        'scope': scope,
        'state': state
    }
    
    url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"
    print(f"Full authorization URL: {url}")

    return {
        "auth_url": url,
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 3600,
        "message": "Visit the auth_url to complete Spotify authentication. Use the access_token for subsequent API calls."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
