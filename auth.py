from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.cloud import firestore
import jwt
from datetime import datetime, timedelta, timezone
import os

SECRET_KEY = os.getenv("SECRET_KEY") 
ALGORITHM = "HS256"

# Security scheme
security = HTTPBearer()

# Initialize Firestore client
db = firestore.Client()

def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify JWT token and check if the session is still active in Firestore
    """
    try:
        # Decode the JWT token
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract session ID from payload
        session_id = payload.get("session_id")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing session_id",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if session exists in Firestore
        session_ref = db.collection('sessions').document(session_id)
        session_doc = session_ref.get()
        
        if not session_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalid",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Optionally check if session has expired based on Firestore timestamp
        session_data = session_doc.to_dict()
        if session_data.get('expires_at') and session_data['expires_at'] < datetime.now(timezone.utc):
            # Clean up expired session
            session_ref.delete()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload
        
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def generate_jwt_and_store_session(session_id: str) -> str:
    """
    Generate JWT token and store session in Firestore
    """
    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(hours=1)
    payload = { 
        "session_id": session_id ,
        "exp": expires_at
    }
    
    # Store session in Firestore 
    session_data = {
        'created_at': created_at,
        'expires_at': expires_at,  
        'active': True
    }
    db.collection('sessions').document(session_id).set(session_data)
    
    # Generate and return JWT token
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def revoke_session(session_id: str):
    """
    Revoke a session by deleting it from Firestore
    """
    db.collection('sessions').document(session_id).delete()

def store_spotify_tokens(session_id: str, access_token: str, refresh_token: str, expires_in: int, scope: str):
    """
    Store Spotify OAuth tokens in an existing session
    """
    session_ref = db.collection('sessions').document(session_id)
    
    # Calculate when the Spotify token expires
    spotify_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    
    # Update the session with Spotify tokens
    spotify_data = {
        'spotify_access_token': access_token,
        'spotify_refresh_token': refresh_token,
        'spotify_token_expires_at': spotify_token_expires_at,
        'spotify_scope': scope,
        'spotify_linked_at': datetime.now(timezone.utc)
    }
    
    session_ref.update(spotify_data)
    
def get_spotify_tokens(session_id: str):
    """
    Get Spotify tokens from a session, refresh if necessary
    Returns None if no Spotify tokens are linked
    """
    session_ref = db.collection('sessions').document(session_id)
    session_doc = session_ref.get()
    
    if not session_doc.exists:
        return None
    
    session_data = session_doc.to_dict()
    
    # Check if Spotify tokens exist
    if not session_data.get('spotify_access_token'):
        return None
    
    # Check if token has expired
    if session_data.get('spotify_token_expires_at') and session_data['spotify_token_expires_at'] < datetime.now(timezone.utc):
        # TODO: Implement token refresh logic here
        # For now, return None for expired tokens
        return None
    
    return {
        'access_token': session_data.get('spotify_access_token'),
        'refresh_token': session_data.get('spotify_refresh_token'),
        'expires_at': session_data.get('spotify_token_expires_at'),
        'scope': session_data.get('spotify_scope')
    }

def store_conversation_message(session_id: str, conversation_id: str, message: str, response: str):
    """
    Store a conversation message and response in Firestore
    """
    conversation_ref = db.collection('conversations').document(f"{session_id}_{conversation_id}")
    
    message_data = {
        'timestamp': datetime.now(timezone.utc),
        'message': message,
        'response': response
    }
    
    # Get existing conversation or create new one
    conversation_doc = conversation_ref.get()
    if conversation_doc.exists:
        # Add to existing conversation
        conversation_ref.update({
            'messages': firestore.ArrayUnion([message_data]),
            'updated_at': datetime.now(timezone.utc)
        })
    else:
        # Create new conversation
        conversation_ref.set({
            'session_id': session_id,
            'conversation_id': conversation_id,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'messages': [message_data]
        })

def get_conversation_history(session_id: str, conversation_id: str, limit: int = 10):
    """
    Get conversation history for a session and conversation ID
    Returns list of messages in chronological order
    """
    conversation_ref = db.collection('conversations').document(f"{session_id}_{conversation_id}")
    conversation_doc = conversation_ref.get()
    
    if not conversation_doc.exists:
        return []
    
    conversation_data = conversation_doc.to_dict()
    messages = conversation_data.get('messages', [])
    
    # Sort by timestamp and limit
    messages.sort(key=lambda x: x['timestamp'])
    return messages[-limit:] if limit else messages

def get_user_conversations(session_id: str):
    """
    Get all conversations for a user session
    """
    conversations = db.collection('conversations').where('session_id', '==', session_id).stream()
    
    conversation_list = []
    for conv in conversations:
        conv_data = conv.to_dict()
        conversation_list.append({
            'conversation_id': conv_data['conversation_id'],
            'created_at': conv_data['created_at'],
            'updated_at': conv_data['updated_at'],
            'message_count': len(conv_data.get('messages', []))
        })
    
    return sorted(conversation_list, key=lambda x: x['updated_at'], reverse=True)