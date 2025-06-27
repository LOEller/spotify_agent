import spotipy
import json
from typing import List
from langchain.tools import Tool


def create_spotify_tools(access_token: str) -> List[Tool]:
    """
    Create LangChain tools for Spotify API access with the access token baked in
    """
    sp = spotipy.Spotify(auth=access_token)
    
    def get_user_profile(input_text: str = ""):
        """Get the user's Spotify profile information"""
        try:
            profile = sp.current_user()
            return json.dumps({
                "name": profile.get("display_name"),
                "id": profile.get("id"),
                "followers": profile.get("followers", {}).get("total", 0),
                "country": profile.get("country")
            })
        except Exception as e:
            return f"Error getting profile: {str(e)}"
    
    def get_user_playlists(input_text: str = ""):
        """Get the user's Spotify playlists"""
        try:
            playlists = sp.current_user_playlists(limit=20)
            playlist_data = []
            for playlist in playlists["items"]:
                playlist_data.append({
                    "name": playlist["name"],
                    "id": playlist["id"],
                    "tracks_total": playlist["tracks"]["total"],
                    "public": playlist["public"]
                })
            return json.dumps(playlist_data)
        except Exception as e:
            return f"Error getting playlists: {str(e)}"
    
    def get_saved_tracks(input_text: str = ""):
        """Get the user's saved tracks (liked songs)"""
        try:
            tracks = sp.current_user_saved_tracks(limit=20)
            track_data = []
            for item in tracks["items"]:
                track = item["track"]
                track_data.append({
                    "name": track["name"],
                    "artist": track["artists"][0]["name"],
                    "album": track["album"]["name"],
                    "id": track["id"]
                })
            return json.dumps(track_data)
        except Exception as e:
            return f"Error getting saved tracks: {str(e)}"
    
    def search_spotify(query: str):
        """Search for tracks, artists, or albums on Spotify"""
        try:
            results = sp.search(q=query, type='track,artist,album', limit=10)
            search_data = {
                "tracks": [],
                "artists": [],
                "albums": []
            }
            
            for track in results["tracks"]["items"]:
                search_data["tracks"].append({
                    "name": track["name"],
                    "artist": track["artists"][0]["name"],
                    "id": track["id"]
                })
            
            for artist in results["artists"]["items"]:
                search_data["artists"].append({
                    "name": artist["name"],
                    "id": artist["id"],
                    "followers": artist["followers"]["total"]
                })
            
            for album in results["albums"]["items"]:
                search_data["albums"].append({
                    "name": album["name"],
                    "artist": album["artists"][0]["name"],
                    "id": album["id"]
                })
            
            return json.dumps(search_data)
        except Exception as e:
            return f"Error searching: {str(e)}"
    
    def get_top_tracks(input_text: str = ""):
        """Get the user's top tracks"""
        try:
            # Parse time range from input if provided
            time_range = 'medium_term'  # default
            if input_text and 'short' in input_text.lower():
                time_range = 'short_term'
            elif input_text and 'long' in input_text.lower():
                time_range = 'long_term'
            
            top_tracks = sp.current_user_top_tracks(limit=20, time_range=time_range)
            track_data = []
            for track in top_tracks["items"]:
                track_data.append({
                    "name": track["name"],
                    "artist": track["artists"][0]["name"],
                    "popularity": track["popularity"],
                    "id": track["id"]
                })
            return json.dumps(track_data)
        except Exception as e:
            return f"Error getting top tracks: {str(e)}"
    
    def get_recently_played(input_text: str = ""):
        """Get the user's recently played tracks"""
        try:
            # Parse limit from input if provided
            limit = 20  # default
            if input_text and any(char.isdigit() for char in input_text):
                numbers = [int(s) for s in input_text.split() if s.isdigit()]
                if numbers:
                    limit = min(numbers[0], 50)  # cap at 50
            
            recent = sp.current_user_recently_played(limit=limit)
            track_data = []
            for item in recent["items"]:
                track = item["track"]
                track_data.append({
                    "name": track["name"],
                    "artist": track["artists"][0]["name"],
                    "played_at": item["played_at"],
                    "id": track["id"]
                })
            return json.dumps(track_data)
        except Exception as e:
            return f"Error getting recently played: {str(e)}"
        
    def play_next_song(input_text: str = ""):
        """Play the next song in the user's queue"""
        try:
            sp.next_track()
            return "Next song queued"
        except Exception as e:
            return f"Error playing next song: {str(e)}"
        
    def add_to_queue(input_text: str = ""):
        """Add a song to the user's queue"""
        try:
            sp.add_to_queue(input_text)
            return "Song added to queue"
        except Exception as e:
            return f"Error adding to queue: {str(e)}"
        
    def get_user_current_track(input_text: str = ""):
        """Get the user's current track"""
        try:
            current_track = sp.current_user_playing_track()
            return json.dumps(current_track)
        except Exception as e:
            return f"Error getting current track: {str(e)}"
    
    # Return the tools with the access token baked in via closures
    return [
        Tool(
            name="get_user_profile",
            func=get_user_profile,
            description="Get the user's Spotify profile information including name, followers, and country. No input required."
        ),
        Tool(
            name="get_user_playlists", 
            func=get_user_playlists,
            description="Get the user's Spotify playlists with names, track counts, and visibility. No input required."
        ),
        Tool(
            name="get_saved_tracks",
            func=get_saved_tracks, 
            description="Get the user's saved/liked tracks from their library. No input required."
        ),
        Tool(
            name="search_spotify",
            func=search_spotify,
            description="Search for tracks, artists, or albums on Spotify. Input should be a search query string."
        ),
        Tool(
            name="get_top_tracks",
            func=get_top_tracks,
            description="Get the user's top tracks based on their listening history. Optional: specify 'short term', 'medium term', or 'long term' for different time ranges."
        ),
        Tool(
            name="get_recently_played",
            func=get_recently_played,
            description="Get the user's recently played tracks. Optional: specify a number to limit results (e.g., 'last 10 songs')."
        ),
        Tool(
            name="play_next_song",
            func=play_next_song,
            description="Play the next song in the user's queue. No input required."
        ),
        Tool(
            name="add_to_queue",
            func=add_to_queue,
            description="Add a song to the user's queue. Input should be a song id, song uri or URL."
        ),
        Tool(
            name="get_user_current_track",
            func=get_user_current_track,
            description="Get the user's current track. No input required."
        )
    ]