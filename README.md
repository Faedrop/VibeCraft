# VibeCraft 🎵

An AI-powered Spotify playlist generator that creates mood-based playlists from your Liked Songs.

## Setup

1.  Clone this repo.
2.  Install dependencies: `pip install -r requirements.txt`
3.  Create a Spotify App at the [Developer Dashboard](https://developer.spotify.com/dashboard/).
4.  Create a `.env` file and add your credentials:
    ```
    SPOTIPY_CLIENT_ID='your_client_id_here'
    SPOTIPY_CLIENT_SECRET='your_client_secret_here'
    SPOTIPY_REDIRECT_URI='http://127.0.0.1:8000/callback'
    ```
5.  Add your Spotify email to your app's "User Management" settings in the dashboard.
6.  Run the script: `python VibeCraft.py`