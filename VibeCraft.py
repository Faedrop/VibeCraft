import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import time
import os 
from dotenv import load_dotenv  

load_dotenv()

# NEW: Get the variables from the environment
CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

# this is for the string of permissions we need
scope = 'user-library-read playlist-modify-private playlist-modify-public '
sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=scope
    ),
    requests_timeout=10 
)
results = sp.current_user()
print(f"Found {results['display_name']}'s profile")


def get_liked_tracks(sp):
    results = sp.current_user_saved_tracks(limit=20)
    tracks_names = []
    tracks_ids = []

    for item in results['items']:
         track = item['track']
         tracks_ids.append(track['id'])
         tracks_names.append(track['name'])

    while results['next']:
        results = sp.next(results)
        for item in results['items']:
            track = item['track']
            tracks_names.append(track['name'])
            tracks_ids.append(track['id'])
    print(f"Total liked tracks: {len(tracks_names)}")
    return tracks_ids, tracks_names
    

def get_audio_features(sp, track_ids):
    chunk_size = 100
    all_audio_features=  []


    for i in range(0, len(track_ids), chunk_size):
        chunk = track_ids[i:i + chunk_size]
        try:
            audio_features = sp.audio_features(chunk)
            if audio_features is not None:  # Check if the response is valid
                all_audio_features.extend(audio_features)
            print(f"Processed {min(i + chunk_size, len(track_ids))}/{len(track_ids)} tracks")
        except Exception as e:
            print(f"Error on chunk {i}: {e}")
            # You can decide to break or continue here
        time.sleep(1)  # WAIT 1 SECOND between API calls

    return all_audio_features

def filter_tracks_by_vibe(df,vibe_name):
    if vibe_name == 'chill':
        filtered_df = df[(df['energy'] < 0.5) & (df['valence'] < 0.5)]
    elif vibe_name == 'happy':
        filtered_df = df[(df['energy'] >= 0.5) & (df['valence'] >= 0.5)]
    elif vibe_name == 'energetic':
        filtered_df = df[(df['energy'] >= 0.5) & (df['valence'] < 0.5)]
    elif vibe_name == 'sad':
        filtered_df = df[(df['energy'] < 0.5) & (df['valence'] >= 0.5)]
    elif vibe_name == 'romantic':
        filtered_df = df[(df['valence'] >= 0.7) & (df['tempo'] < 100)]
    elif vibe_name == 'aggressive':
        filtered_df = df[(df['energy'] >= 0.7) & (df['tempo'] >= 120)]
    else:
        raise ValueError("Vibe name must be one of: 'chill', 'happy', 'energetic', 'sad', 'romantic', 'aggressive') ")

    print(f"Filtered down to {len(filtered_df)} '{vibe_name}' tracks")
    return filtered_df


def create_playlist(sp, track_uris, vibe_name):
    user_id = sp.current_user()['id']
    playlist = sp.user_playlist_create(
        user = user_id,
        name = "My VibeCraft " + vibe_name + " Playlist",
        public = True,
        description = f"A playlist of my {vibe_name} tracks, created with VibeCraft!"
    )
    
    print(f"Created playlist: {playlist['name']}")
    print(f"Playlist ID: {playlist['id']}")
    print(f"Playlist URL: {playlist['external_urls']['spotify']}")

    playlist_id = playlist['id']
    print(f"New playlist ID: {playlist_id}")

    track_uris = [f"spotify:track:{tid}" for tid in track_uris]

    print(f"First few URIs: {track_uris[:3]}")
    
    chunk_size = 100
    for i in range(0, len(track_uris), chunk_size):
        chunk = track_uris[i:i + chunk_size]
        sp.playlist_add_items(playlist_id, chunk)  
        print(f"Added {min(i + chunk_size, len(track_uris))}/{len(track_uris)} tracks")
    
    print(f"Added all {len(track_uris)} tracks to the playlist!")
    
    return playlist_id


if __name__ == "__main__":

    track_ids, track_names = get_liked_tracks(sp)
    audio_features = get_audio_features(sp, track_ids)
    df = pd.DataFrame(audio_features)

    # creating dataframe
    df['name'] = track_names
    df = df[['id', 'name', 'danceability', 'energy', 'valence', 'tempo', 'instrumentalness']]
    print(f"Created DataFrame with {len(df)} tracks!")
    print(df.head())
   
    input_vibe = input("Enter your desired vibe (chill, happy, energetic, sad, romantic, aggressive): ").strip().lower()
    filtered_df = filter_tracks_by_vibe(df, input_vibe)
    create_playlist(sp, filtered_df['id'].tolist(), input_vibe)
    print(f"Added {len(filtered_df)} tracks to the playlist!")
    