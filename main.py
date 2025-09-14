import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

# Spotify Setup (same as before)
CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

scope = 'user-library-read playlist-modify-private playlist-modify-public'

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=scope
    ),
    requests_timeout=30
)

def get_lastfm_track_info(artist, track, api_key):
    """Get track info from Last.fm API (free, no restrictions)"""
    url = "http://ws.audioscrobbler.com/2.0/"
    params = {
        'method': 'track.getInfo',
        'api_key': api_key,
        'artist': artist,
        'track': track,
        'format': 'json'
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if 'track' in data:
                track_info = data['track']
                return {
                    'playcount': int(track_info.get('playcount', 0)),
                    'listeners': int(track_info.get('listeners', 0)),
                    'tags': [tag['name'].lower() for tag in track_info.get('toptags', {}).get('tag', [])]
                }
    except Exception as e:
        print(f"Last.fm API error for {artist} - {track}: {e}")
    
    return None

def analyze_track_with_multiple_sources(track_data, lastfm_api_key=None):
    """Combine Spotify + Last.fm data for better analysis"""
    

    spotify_features = {
        'name': track_data['name'],
        'artist': track_data['artist'],
        'popularity': track_data['popularity'],
        'duration_ms': track_data['duration_ms'],
        'genres': track_data.get('genres', []),
        'explicit': track_data.get('explicit', False)
    }
    
    # Get Last.fm data if API key provided
    lastfm_data = {}
    if lastfm_api_key:
        lastfm_info = get_lastfm_track_info(
            track_data['artist'], 
            track_data['name'], 
            lastfm_api_key
        )
        if lastfm_info:
            lastfm_data = lastfm_info
    
    # Calculate composite features
    features = calculate_mood_features(spotify_features, lastfm_data)
    return features

def calculate_mood_features(spotify_data, lastfm_data):
    """Create mood features from available data"""
    
    # Base features from Spotify
    popularity = spotify_data['popularity'] / 100.0
    duration_sec = spotify_data['duration_ms'] / 1000.0
    genres = ' '.join(spotify_data['genres']).lower()
    
    # Enhanced features with Last.fm
    playcount = lastfm_data.get('playcount', 0)
    listeners = lastfm_data.get('listeners', 0)
    tags = ' '.join(lastfm_data.get('tags', [])).lower()
    
    # Calculate mood scores (0-1 scale)
    features = {}
    
    # ENERGY estimation
    energy_score = 0.5  # baseline
    
    # Genre-based energy
    if any(word in genres for word in ['rock', 'metal', 'punk', 'electronic', 'dance', 'edm']):
        energy_score += 0.3
    if any(word in genres for word in ['acoustic', 'folk', 'ambient', 'chill']):
        energy_score -= 0.2
    
    # Tag-based energy (from Last.fm)
    if any(word in tags for word in ['energetic', 'upbeat', 'fast', 'aggressive']):
        energy_score += 0.2
    if any(word in tags for word in ['slow', 'calm', 'peaceful', 'relaxing']):
        energy_score -= 0.2
        
    # Duration-based (shorter songs often more energetic)
    if duration_sec < 180:  # < 3 minutes
        energy_score += 0.1
    elif duration_sec > 300:  # > 5 minutes
        energy_score -= 0.1
    
    features['energy'] = max(0, min(1, energy_score))
    
    # VALENCE (happiness) estimation
    valence_score = 0.5  # baseline
    
    # Genre-based valence
    if any(word in genres for word in ['pop', 'dance', 'disco', 'funk']):
        valence_score += 0.3
    if any(word in genres for word in ['blues', 'emo', 'doom', 'black metal']):
        valence_score -= 0.3
    
    # Tag-based valence
    if any(word in tags for word in ['happy', 'uplifting', 'positive', 'cheerful']):
        valence_score += 0.2
    if any(word in tags for word in ['sad', 'melancholy', 'depressing', 'dark']):
        valence_score -= 0.2
    
    # Popularity can indicate positive reception
    valence_score += (popularity - 0.5) * 0.2
    
    features['valence'] = max(0, min(1, valence_score))
    
    # DANCEABILITY estimation
    dance_score = 0.5  # baseline
    
    if any(word in genres for word in ['dance', 'electronic', 'disco', 'funk', 'pop']):
        dance_score += 0.4
    if any(word in tags for word in ['danceable', 'groovy', 'rhythmic']):
        dance_score += 0.2
    
    features['danceability'] = max(0, min(1, dance_score))
    
    # TEMPO estimation (relative)
    tempo_score = 0.5
    if any(word in genres + ' ' + tags for word in ['fast', 'uptempo', 'energetic']):
        tempo_score += 0.3
    if any(word in genres + ' ' + tags for word in ['slow', 'ballad', 'downtempo']):
        tempo_score -= 0.3
        
    features['tempo'] = max(0, min(1, tempo_score))
    
    return features

def classify_vibe_advanced(features):
    """Advanced vibe classification using calculated features"""
    energy = features['energy']
    valence = features['valence']
    dance = features['danceability']
    tempo = features['tempo']
    
    # More nuanced classification
    if energy > 0.7 and valence > 0.6 and dance > 0.6:
        return 'happy'
    elif energy < 0.4 and valence < 0.4:
        return 'sad'
    elif energy > 0.6 and tempo > 0.6:
        return 'energetic'
    elif energy < 0.5 and valence > 0.4 and valence < 0.7:
        return 'chill'
    elif valence > 0.6 and energy < 0.6 and dance > 0.4:
        return 'romantic'
    elif energy > 0.7 and valence < 0.5:
        return 'aggressive'
    else:
        return 'chill'  # default
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
def get_liked_tracks_with_details(sp):
    """Return a list of dicts with id, name, artist name, and popularity for each liked track."""
    results = sp.current_user_saved_tracks(limit=20)
    tracks = []

    def extract_track(item):
        track = item['track']
        return {
            'id': track['id'],
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'popularity': track.get('popularity', 0),
            'duration_ms': track.get('duration_ms', 0),
            'explicit': track.get('explicit', False)
        }

    for item in results['items']:
        tracks.append(extract_track(item))

    while results['next']:
        results = sp.next(results)
        for item in results['items']:
            tracks.append(extract_track(item))
    print(f"Total liked tracks: {len(tracks)}")
    return tracks

def get_artist_genres_batch(sp, tracks_data):
    """Add artist genres to each track in tracks_data, caching by artist name."""
    artist_genre_cache = {}
    for track in tracks_data:
        artist_name = track.get('artist', None)
        if not artist_name:
            track['genres'] = []
            continue
        if artist_name in artist_genre_cache:
            track['genres'] = artist_genre_cache[artist_name]
            continue
        try:
            results = sp.search(q=f"artist:{artist_name}", type='artist', limit=1)
            if results['artists']['items']:
                artist_info = results['artists']['items'][0]
                genres = artist_info.get('genres', [])
            else:
                genres = []
            artist_genre_cache[artist_name] = genres
            track['genres'] = genres
        except Exception as e:
            print(f"Error fetching genres for {artist_name}: {e}")
            track['genres'] = []
    return tracks_data

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
    

def main():
    print("🎵 VibeCraft - Advanced Multi-API Version")
    print("Using Spotify + Last.fm for enhanced analysis\n")
    
   
    lastfm_key = os.getenv('LASTFM_API_KEY')  # Add to your .env file
    if lastfm_key:
        print("✅ Last.fm API key found - enhanced analysis enabled")
    else:
        print("ℹ️  No Last.fm API key - using Spotify data only")
        print("💡 Get a free Last.fm API key at: https://www.last.fm/api/account/create")
    
    try:
        user = sp.current_user()
        print(f"✅ Connected to Spotify as: {user['display_name']}\n")
    except Exception as e:
        print(f"❌ Spotify connection failed: {e}")
        return
    
   
    print("📀 Fetching your liked tracks...")
    tracks_data = get_liked_tracks_with_details(sp)
    if not tracks_data:
        print("❌ No tracks found!")
        return
    print(f"✅ Found {len(tracks_data)} tracks")

    
    tracks_data = get_artist_genres_batch(sp, tracks_data)

    # Analyze tracks in batches
    print("🔍 Analyzing tracks for mood classification...")
    analyzed_tracks = []
    batch_size = 100

    for batch_start in range(0, len(tracks_data), batch_size):
        batch = tracks_data[batch_start:batch_start + batch_size]
        for i, track in enumerate(batch):
            features = analyze_track_with_multiple_sources(track, lastfm_key)
            vibe = classify_vibe_advanced(features)
            track['vibe'] = vibe
            track['features'] = features
            analyzed_tracks.append(track)
            time.sleep(0.1)  # Be nice to Last.fm API
        print(f"✅ Analyzed {min(batch_start + batch_size, len(tracks_data))}/{len(tracks_data)} tracks...")

  
    df = pd.DataFrame(analyzed_tracks)
    
    
    vibe_counts = df['vibe'].value_counts()
    print(f"\n📊 Mood Analysis Results:")
    for vibe, count in vibe_counts.items():
        print(f"  {vibe}: {count} tracks")
    

    chosen_vibe = input(f"\nChoose a vibe {list(vibe_counts.keys())}: ").lower().strip()
    
    if chosen_vibe in vibe_counts.keys():
        vibe_tracks = df[df['vibe'] == chosen_vibe]
        track_ids = vibe_tracks['id'].tolist()
        
        print(f"\n🎧 Creating {chosen_vibe} playlist with {len(track_ids)} tracks...")
        create_playlist(sp, track_ids, chosen_vibe)
    else:
        print("Invalid vibe selection!")


if __name__ == "__main__":
    main()