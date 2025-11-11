"""
Spotify Advanced Music Analyzer - Enterprise Edition
====================================================
Enhanced with:
- Robust error handling and logging
- Performance optimizations with better caching
- Type hints and documentation
- Configuration management
- Rate limiting protection
- Data validation
- Better UX with progressive loading
"""

import streamlit as st
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from collections import Counter, defaultdict
import json
from datetime import datetime
import os
from typing import Dict, List, Tuple, Optional, Any
import statistics
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import traceback
from pydantic import BaseModel, ValidationError, Field
import logging
from dataclasses import dataclass
from functools import wraps
import time

# ========================================
# CONFIGURATION & LOGGING
# ========================================

@dataclass
class AppConfig:
    """Application configuration"""
    REDIRECT_URI: str = "http://127.0.0.1:8888/callback"
    CACHE_TTL: int = 3600  # 1 hour
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2
    PLAYLIST_TARGET_SIZE: int = 10
    GEMINI_PLAYLIST_REQUEST_SIZE: int = 15
    
config = AppConfig()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========================================
# DECORATORS & UTILITIES
# ========================================

def retry_on_error(max_retries: int = 3, delay: int = 2):
    """Retry decorator for API calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts: {e}")
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

def safe_get(data: Dict, *keys, default=None):
    """Safely navigate nested dictionaries"""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data

# ========================================
# PYDANTIC MODELS
# ========================================

class Song(BaseModel):
    """Song model for playlist generation"""
    artist: str = Field(..., min_length=1, max_length=200)
    track: str = Field(..., min_length=1, max_length=200)

class Playlist(BaseModel):
    """Playlist model with validation"""
    songs: List[Song] = Field(..., min_items=1, max_items=50)

class TrackInfo(BaseModel):
    """Validated track information"""
    id: str
    name: str
    artists: List[str]
    album: str
    popularity: int = 0
    release_date: str = ""

# ========================================
# SPOTIFY ANALYZER CLASS (ENHANCED)
# ========================================

class SpotifyAdvancedAnalyzer:
    """Enhanced Spotify API analyzer with enterprise features"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """Initialize Spotify analyzer with error handling"""
        try:
            cache_path = ".spotify_cache"
            self.scope = "user-top-read playlist-read-private user-read-recently-played user-library-read playlist-modify-public"
            
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=self.scope,
                cache_path=cache_path,
                open_browser=True,
                show_dialog=True
            ))
            
            user_data = self.sp.current_user()
            self.user_id = user_data['id']
            self.user_name = user_data.get('display_name', 'User')
            logger.info(f"Successfully authenticated as {self.user_name}")
            
        except Exception as e:
            logger.error(f"Spotify authentication failed: {e}")
            st.error(f"❌ Spotify bağlantı hatası: {e}")
            st.stop()

    # ========================================
    # DATA FETCHING (ENHANCED)
    # ========================================
    
    @retry_on_error(max_retries=3)
    def get_top_tracks(self, time_range: str = 'short_term', limit: int = 50) -> List[Dict]:
        """Fetch top tracks with retry logic"""
        try:
            results = self.sp.current_user_top_tracks(time_range=time_range, limit=limit)
            tracks = [
                track for track in results.get('items', [])
                if isinstance(track, dict) and track.get('id')
            ]
            logger.info(f"Fetched {len(tracks)} top tracks for {time_range}")
            return tracks
        except Exception as e:
            logger.error(f"Error fetching top tracks: {e}")
            return []

    @retry_on_error(max_retries=3)
    def get_top_artists(self, time_range: str = 'short_term', limit: int = 50) -> List[Dict]:
        """Fetch top artists with validation"""
        try:
            results = self.sp.current_user_top_artists(time_range=time_range, limit=limit)
            return results.get('items', [])
        except Exception as e:
            logger.error(f"Error fetching top artists: {e}")
            return []
    
    @retry_on_error(max_retries=3)
    def get_recently_played(self, limit: int = 50) -> List[Dict]:
        """Fetch recently played tracks"""
        try:
            results = self.sp.current_user_recently_played(limit=limit)
            return results.get('items', [])
        except Exception as e:
            logger.error(f"Error fetching recently played: {e}")
            return []
    
    def get_saved_tracks_count(self) -> int:
        """Get count of saved tracks safely"""
        try:
            return self.sp.current_user_saved_tracks(limit=1).get('total', 0)
        except Exception as e:
            logger.warning(f"Could not fetch saved tracks count: {e}")
            return 0
    
    @retry_on_error(max_retries=3)
    def get_user_playlists(self) -> List[Dict]:
        """Fetch all user playlists with pagination"""
        playlists = []
        try:
            results = self.sp.current_user_playlists(limit=50)
            while results:
                playlists.extend(results.get('items', []))
                if results.get('next'):
                    results = self.sp.next(results)
                else:
                    break
            
            # Filter user's own playlists or collaborative ones
            user_playlists = [
                p for p in playlists 
                if p and (safe_get(p, 'owner', 'id') == self.user_id or p.get('collaborative'))
            ]
            logger.info(f"Fetched {len(user_playlists)} user playlists")
            return user_playlists
            
        except Exception as e:
            logger.error(f"Error fetching playlists: {e}")
            return []
    
    @st.cache_data(show_spinner=False, ttl=config.CACHE_TTL)
    def get_all_saved_tracks(_self) -> List[Dict]:
        """Fetch all saved tracks with progress indication"""
        tracks = []
        try:
            results = _self.sp.current_user_saved_tracks(limit=50)
            progress = st.progress(0, text="Kütüphanenizdeki tüm şarkılar çekiliyor...")
            
            total_tracks = results.get('total', 0)
            fetched = 0
            
            while results:
                items = results.get('items', [])
                tracks.extend([
                    item['track'] for item in items 
                    if isinstance(safe_get(item, 'track'), dict) and safe_get(item, 'track', 'id')
                ])
                
                fetched += len(items)
                if total_tracks > 0:
                    progress.progress(min(fetched / total_tracks, 1.0))
                
                if results.get('next'):
                    results = _self.sp.next(results)
                else:
                    break
            
            progress.empty()
            logger.info(f"Fetched {len(tracks)} saved tracks")
            st.toast(f"✅ {len(tracks)} adet kayıtlı şarkı bulundu.")
            
        except Exception as e:
            logger.error(f"Error fetching saved tracks: {e}")
            st.error(f"Kütüphane çekilirken hata: {e}")
        
        return tracks
    
    @st.cache_data(show_spinner=False, ttl=config.CACHE_TTL)
    def get_playlist_tracks(_self, playlist_id: str) -> List[Dict]:
        """Fetch all tracks from a playlist with progress"""
        tracks = []
        try:
            results = _self.sp.playlist_tracks(playlist_id, limit=100)
            progress = st.progress(0, text="Çalma listesi şarkıları çekiliyor...")
            
            total = results.get('total', 0)
            fetched = 0
            
            while results:
                items = results.get('items', [])
                tracks.extend([
                    item['track'] for item in items 
                    if isinstance(safe_get(item, 'track'), dict) and safe_get(item, 'track', 'id')
                ])
                
                fetched += len(items)
                if total > 0:
                    progress.progress(min(fetched / total, 1.0))
                
                if results.get('next'):
                    results = _self.sp.next(results)
                else:
                    break
            
            progress.empty()
            logger.info(f"Fetched {len(tracks)} playlist tracks")
            st.toast(f"✅ {len(tracks)} adet şarkı bulundu.")
            
        except Exception as e:
            logger.error(f"Error fetching playlist tracks: {e}")
            st.error(f"Çalma listesi çekilirken hata: {e}")
        
        return tracks

    @st.cache_data(show_spinner=False, ttl=config.CACHE_TTL)
    def get_all_user_tracks_heavy(_self) -> List[Dict]:
        """Fetch ALL user tracks (library + all playlists) with progress"""
        all_tracks_dict = {}
        
        # Phase 1: Saved tracks
        with st.spinner("1/3: Beğenilen Şarkılar çekiliyor..."):
            saved_tracks = _self.get_all_saved_tracks()
            for track in saved_tracks:
                if track and track.get('id'):
                    all_tracks_dict[track['id']] = track
            st.toast(f"✅ {len(all_tracks_dict)} beğenilen şarkı eklendi.")

        # Phase 2: Get playlists
        with st.spinner("2/3: Çalma listeleri bulunuyor..."):
            playlists = _self.get_user_playlists()
            st.toast(f"✅ {len(playlists)} adet çalma listesi bulundu.")

        # Phase 3: Scan all playlists
        if playlists:
            progress_bar = st.progress(0, text="3/3: Çalma listeleri taranıyor...")
            
            for i, playlist in enumerate(playlists):
                playlist_name = safe_get(playlist, 'name', default='Bilinmeyen Liste')
                progress_bar.progress((i + 1) / len(playlists), 
                                     text=f"Taranıyor: {playlist_name} ({i+1}/{len(playlists)})")
                
                try:
                    playlist_tracks = _self.get_playlist_tracks(playlist['id'])
                    for track in playlist_tracks:
                        if track and track.get('id'):
                            all_tracks_dict[track['id']] = track
                except Exception as e:
                    logger.warning(f"Error scanning playlist '{playlist_name}': {e}")
                    st.warning(f"⚠️ '{playlist_name}' taranırken hata: {e}")
            
            progress_bar.empty()
        
        unique_count = len(all_tracks_dict)
        logger.info(f"Total unique tracks found: {unique_count}")
        st.success(f"✅ Tarama tamamlandı! {unique_count} adet EŞSİZ şarkı bulundu.")
        
        return list(all_tracks_dict.values())
        
    # ========================================
    # DATA SANITIZATION (ENHANCED)
    # ========================================
    
    def sanitize_track_list(self, tracks: List) -> List[Dict]:
        """
        Cleans and *patches* a list of raw track items.
        It trims faulty data but does not discard the track if an ID exists.
        
        Gelen 'kirli' şarkı listesini (wrapper'lar, bozuk veriler) alır ve
        gerekli alanları 'yamayarak' %100 temiz bir liste döndürür.
        """
        clean_tracks = []
        if not tracks:
            logger.warning("Sanitization için boş şarkı listesi sağlandı")
            return []

        invalid_count = 0 # Tamamen kurtarılamayan (ID'si olmayan)
        patched_count = 0 # Kurtarılan ama yamalanan

        for item in tracks:
            track_obj = None
            
            # 1. Adım: Şarkı objesini (track_obj) çıkar
            if isinstance(item, dict):
                if 'track' in item and isinstance(item.get('track'), dict):
                    track_obj = item['track'] # Bu bir wrapper: {'track': {...}}
                elif 'id' in item:
                    track_obj = item # Bu doğrudan bir track objesi: {'id': ...}
            
            # 2. Adım: Eğer bir şarkı objesi yapısı bulamadıysak (örn: 'True' veya 'None' ise)
            if not track_obj:
                invalid_count += 1
                continue
                
            # 3. Adım: VALIDATE (Doğrula) - Tek Kural: ID'si olmalı
            # Eğer bir ID yoksa, bu öğe kurtarılamaz.
            if not track_obj.get('id'):
                invalid_count += 1
                continue
            
            # 4. Adım: PATCH (Yama) - Veriyi kaybetme, düzelt!
            # Diğer analiz fonksiyonlarının (popularity, genres) çökmemesi için
            # eksik alanları varsayılan değerlerle doldur.
            
            is_patched = False
            
            # İsim kontrolü
            if not track_obj.get('name'): # (None veya "")
                track_obj['name'] = "İsimsiz Parça"
                is_patched = True
            
            # Sanatçı kontrolü
            if not track_obj.get('artists') or not isinstance(track_obj['artists'], list) or not track_obj['artists']:
                track_obj['artists'] = [{'id': None, 'name': 'Bilinmeyen Sanatçı'}]
                is_patched = True
            
            # Albüm kontrolü
            if not track_obj.get('album') or not isinstance(track_obj['album'], dict):
                track_obj['album'] = {'name': 'Bilinmeyen Albüm', 'release_date': '1900'}
                is_patched = True
            
            # Popülerlik kontrolü
            if 'popularity' not in track_obj:
                track_obj['popularity'] = 0
                is_patched = True
                
            if is_patched:
                patched_count += 1
            
            # Temiz listeye sadece %100 güvenli ve yamalanmış objeyi ekle
            clean_tracks.append(track_obj)

        if invalid_count > 0:
            logger.info(f"Filtrelendi: {invalid_count} adet kurtarılamayan öğe (ID'siz veya bozuk format)")
        if patched_count > 0:
            logger.info(f"Yamalandı: {patched_count} adet şarkıda eksik alanlar (isim, sanatçı vb.) düzeltildi")
            
        logger.info(f"Temizlendi: {len(tracks)} öğe -> {len(clean_tracks)} geçerli şarkı")
        
        # Streamlit'e de bilgi verelim
        st.toast(f"ℹ️ {invalid_count} bozuk öğe atlandı, {patched_count} şarkı yamalandı.")
        
        return clean_tracks
    
    # def _validate_track_object(self, track: Dict) -> bool:
    #     """Validate that track object has minimum required fields"""
    #     required_fields = ['id', 'name']
    #     return all(track.get(field) for field in required_fields)

    # ========================================
    # ANALYSIS FUNCTIONS (ENHANCED)
    # ========================================

    # def get_audio_features(self, tracks: List[Dict]) -> Optional[Dict[str, float]]:
    #     """Get audio features with batch processing and error handling"""
    #     track_ids = [track.get('id') for track in tracks if track.get('id')]
        
    #     if not track_ids:
    #         logger.warning("No valid track IDs for audio features")
    #         return None
        
    #     try:
    #         all_features = []
    #         # Process in batches of 50 (Spotify API limit)
    #         for i in range(0, len(track_ids), 50):
    #             batch = track_ids[i:i+50]
    #             features = self.sp.audio_features(batch)
    #             all_features.extend([f for f in features if f is not None])
            
    #         if not all_features:
    #             logger.warning("No audio features returned from API")
    #             return None

    #         # Calculate averages
    #         metrics = {
    #             'danceability': [],
    #             'energy': [],
    #             'valence': [],
    #             'acousticness': [],
    #             'instrumentalness': [],
    #             'speechiness': [],
    #             'tempo': []
    #         }
            
    #         for feature in all_features:
    #             for key in metrics.keys():
    #                 value = feature.get(key)
    #                 if value is not None:
    #                     metrics[key].append(value)
            
    #         averages = {
    #             key: statistics.mean(values) 
    #             for key, values in metrics.items() 
    #             if values
    #         }
            
    #         logger.info(f"Calculated audio features for {len(all_features)} tracks")
    #         return averages
            
    #     except Exception as e:
    #         logger.error(f"Error calculating audio features: {e}")
    #         st.error(f"Ses özellikleri alınırken hata: {e}")
    #         return None
    
    def analyze_genres(self, tracks: List[Dict]) -> Tuple[Counter, Counter, Dict]:
        """Analyze genres with artist information"""
        genre_counter = Counter()
        artist_counter = Counter()
        genre_by_artist = defaultdict(set)
        
        processed_artists = set()
        
        for track in tracks:
            artists = track.get('artists', [])
            
            for artist in artists:
                if not isinstance(artist, dict) or not artist.get('id'):
                    continue
                
                artist_id = artist['id']
                artist_name = artist.get('name', 'Unknown')
                artist_counter[artist_name] += 1
                
                # Avoid duplicate API calls
                if artist_id in processed_artists:
                    continue
                
                processed_artists.add(artist_id)
                
                try:
                    artist_info = self.sp.artist(artist_id)
                    genres = artist_info.get('genres', [])
                    
                    for genre in genres:
                        genre_counter[genre] += 1
                        genre_by_artist[genre].add(artist_name)
                        
                except Exception as e:
                    logger.debug(f"Could not fetch artist info for {artist_name}: {e}")
                    continue
        
        logger.info(f"Analyzed {len(genre_counter)} genres from {len(artist_counter)} artists")
        return genre_counter, artist_counter, genre_by_artist
    
    def analyze_popularity(self, tracks: List[Dict]) -> Optional[Dict[str, float]]:
        """Analyze track popularity statistics"""
        popularities = [
            track.get('popularity', 0) 
            for track in tracks 
            if track.get('popularity')
        ]
        
        if not popularities:
            logger.warning("No popularity data available")
            return None
        
        stats = {
            'avg': statistics.mean(popularities),
            'max': max(popularities),
            'min': min(popularities),
            'median': statistics.median(popularities)
        }
        
        logger.info(f"Popularity stats: avg={stats['avg']:.1f}, range={stats['min']}-{stats['max']}")
        return stats
    
    def get_decade_distribution(self, tracks: List[Dict]) -> Counter:
        """Analyze track distribution by decade"""
        decades = Counter()
        
        for track in tracks:
            release_date = safe_get(track, 'album', 'release_date', default='')
            
            if release_date and len(release_date) >= 4:
                try:
                    year = int(release_date[:4])
                    decade = (year // 10) * 10
                    decades[f"{decade}'ler"] += 1
                except (ValueError, TypeError):
                    continue
        
        logger.info(f"Decade distribution: {len(decades)} decades found")
        return decades
    
    # def create_mood_profile(self, audio_features: Optional[Dict]) -> str:
    #     """Create mood profile from audio features"""
    #     if not audio_features:
    #         return "Veri Yetersiz 🎵"
        
    #     energy = audio_features.get('energy', 0)
    #     valence = audio_features.get('valence', 0)
    #     danceability = audio_features.get('danceability', 0)
        
    #     # Mood classification logic
    #     if energy > 0.7 and danceability > 0.7:
    #         return "Enerjik ve Dans Edilebilir 🎉"
    #     elif valence > 0.7:
    #         return "Neşeli ve Pozitif 😊"
    #     elif energy < 0.4 and valence < 0.4:
    #         return "Sakin ve Melankolik 🌙"
    #     elif energy > 0.6 and valence < 0.5:
    #         return "Yoğun ve Duygusal 🔥"
    #     else:
    #         return "Dengeli ve Çeşitli 🎵"

    # ========================================
    # REPORT GENERATION (ENHANCED)
    # ========================================

    def get_top_tracks_and_artists(self, time_range: str = 'short_term') -> Tuple[List[Dict], List[Dict]]:
        """Fetch top tracks and artists for a time range"""
        top_tracks = self.get_top_tracks(time_range, limit=50)
        top_artists_api = self.get_top_artists(time_range, limit=50)
        
        top_artists_data = [
            {
                'name': artist.get('name', 'Unknown'),
                'popularity': artist.get('popularity', 0),
                'followers': safe_get(artist, 'followers', 'total', default=0),
                'genres': artist.get('genres', [])
            }
            for artist in top_artists_api
        ]
        
        return top_tracks, top_artists_data
    
    def run_analysis_on_tracklist(
        self, 
        tracks: List, 
        analysis_title: str, 
        top_artists_override: Optional[List[Dict]] = None
    ) -> Optional[Dict]:
        """
        Run comprehensive analysis on track list
        Returns structured report data
        """
        # Sanitize input
        clean_tracks = self.sanitize_track_list(tracks)
        
        if not clean_tracks:
            logger.error("No valid tracks after sanitization")
            st.error("❌ Geçerli şarkı bulunamadı. Analiz durduruluyor.")
            return None
        
        logger.info(f"Analyzing {len(clean_tracks)} clean tracks")
        st.toast(f"📊 {len(clean_tracks)} şarkı analiz ediliyor...")
        
        # Run core analyses
        with st.spinner("Tür ve sanatçı analizi yapılıyor..."):
            genre_counter, artist_counter, genre_by_artist = self.analyze_genres(clean_tracks)
        
        popularity_stats = self.analyze_popularity(clean_tracks)
        decade_dist = self.get_decade_distribution(clean_tracks)
        
        # Prepare top artists
        top_artists_data = []
        if top_artists_override:
            top_artists_data = top_artists_override
        else:
            top_artists_data = [
                {
                    'name': f"{artist_name} ({count} şarkı)",
                    'popularity': 0,
                    'followers': 0,
                    'genres': []
                }
                for artist_name, count in artist_counter.most_common(20)
            ]
        
        # Build report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'time_range': analysis_title,
            'user': self.user_name,
            'genres': dict(genre_counter.most_common(20)),
            'genre_by_artist': {k: list(v) for k, v in genre_by_artist.items()},
            'top_artists': top_artists_data,
            'top_tracks': [
                {
                    'name': track.get('name', 'Unknown'),
                    'artists': [a.get('name', 'Unknown') for a in track.get('artists', [])],
                    'album': safe_get(track, 'album', 'name', default='Unknown')
                }
                for track in clean_tracks[:20]
            ],
            'popularity_stats': popularity_stats,
            'decade_distribution': dict(decade_dist),
            'statistics': {
                'total_library_saved_tracks': self.get_saved_tracks_count(),
                'unique_genres': len(genre_counter),
                'unique_artists': len(artist_counter),
                'analyzed_tracks': len(clean_tracks),
                'recent_tracks': len(self.get_recently_played(limit=50))
            }
        }
        
        logger.info(f"Report generated successfully for '{analysis_title}'")
        return report_data

# ========================================
# GEMINI ANALYZER CLASS (ENHANCED)
# ========================================

class GeminiReportAnalyzer:
    """Enhanced Gemini AI analyzer with better error handling"""
    
    def __init__(self, api_key: str):
        """Initialize Gemini with safety settings"""
        try:
            genai.configure(api_key=api_key)
            
            generation_config = genai.types.GenerationConfig(
                temperature=0.1,
                top_p=0.95,
                top_k=30
            )
            
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            self.model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            self.chat = self.model.start_chat(history=[])
            logger.info("Gemini model initialized successfully")
            
        except Exception as e:
            logger.error(f"Gemini initialization failed: {e}")
            st.error(f"❌ Gemini modeli başlatılamadı: {e}")
            self.model = None

    def generate_insights(self, report_data: Dict) -> Tuple[Optional[str], Optional[Dict]]:
        """Generate music profile insights from report data"""
        if not self.model:
            return None, None
        
        try:
            json_data = json.dumps(report_data, ensure_ascii=False, indent=2)
            
            prompt = f"""
Sen bir müzik psikoloğu ve uzman bir veri analistisin. Görevi, bir kullanıcının Spotify dinleme alışkanlıkları hakkında sana verilen JSON verilerini analiz etmek ve bu verilere dayanarak samimi, akıcı ve anlayışlı bir dille bir "müzik profili" çıkarmaktır. Verileri YORUMLA.

Lütfen aşağıdaki yapıya benzer bir analiz yap:

1. **Giriş (Genel Profil):** Kullanıcının genel müzik zevkini, türlere ve sanatçılara bakarak kısaca özetle.
2. **Tür Analizi:** En çok dinlenen türlere bak. Bu türler kullanıcının kişiliği hakkında ne söylüyor olabilir?
3. **Sanatçı ve Popülerlik:** Top sanatçılara ve popülerlik istatistiklerine bak. Kullanıcı popüler (mainstream) mi, yoksa daha az bilinen (niche/underground) sanatçıları mı keşfetmeyi seviyor?
4. **Zaman Yolculuğu (Decade Distribution):** Hangi on yıldan müzik dinlediği onun nostaljik mi yoksa yenilikçi mi olduğunu gösteriyor?
5. **Kapanış ve Öneri:** Tüm bu bilgilere dayanarak kullanıcıya kısa bir özet ve belki bir müzik önerisi sun.   

İşte analiz edilecek veri:

```json
{json_data}
```

Şimdi, bu verilere dayanarak akıcı bir metin halinde analizini oluştur:
"""
            
            response = self.chat.send_message(prompt)
            
            if response.parts:
                text_output = response.text
                usage = response.usage_metadata
                usage_metrics = {
                    "prompt_tokens": usage.prompt_token_count,
                    "response_tokens": usage.candidates_token_count,
                    "total_tokens": usage.total_token_count
                }
                
                logger.info(f"Generated insights: {usage_metrics['total_tokens']} tokens")
                return text_output, usage_metrics
            else:
                logger.warning(f"Gemini response blocked: {response.prompt_feedback}")
                st.error(f"❌ Gemini Yanıtı Engellendi! Sebep: {response.prompt_feedback}")
                return "Analiz, içerik filtrelemesi nedeniyle engellendi.", None
                
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            st.error(f"❌ Gemini analizi sırasında hata: {e}")
            return None, None
    
    def generate_personalized_playlist(
        self, 
        report_data: Dict, 
        playlist_name: str = "Önerilen Müzik Listem"
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Generate personalized playlist recommendations
        Returns JSON string and usage metrics
        """
        if not self.model:
            return None, None

        try:
            json_data = json.dumps(report_data, ensure_ascii=False, indent=2)
            
            # Extract top genres for better prompting
            top_genres = list(report_data.get('genres', {}).keys())[:3]
            genre_hint = ', '.join(top_genres) if top_genres else "kullanıcının türleri"
            
            prompt = f"""
Sen, Spotify'ın "Haftalık Keşif" (Discover Weekly) listelerini tasarlayan uzman bir müzik veri bilimcisi ve küratörüsün. Görevin, bir kullanıcının dinleme verilerini (JSON) analiz edip, onun *henüz keşfetmediği* ama müzik zevkine (türler, ses özellikleri, sanatçılar) dayanarak seveceği şarkıları bulmaktır.

**GÖREV:**
Aşağıdaki verileri analiz et. Bu analize dayanarak, '{playlist_name}' adını verdiğimiz liste için **{config.GEMINI_PLAYLIST_REQUEST_SIZE} ADET** şarkı öner. (Bazıları bulunamayabilir, o yüzden {config.PLAYLIST_TARGET_SIZE}'dan fazla öner.)

**KRİTİK KURALLAR:**
1. **YENİLİKÇİ OL**: Önerdiğin şarkılar, kullanıcının top_artists veya top_tracks listesindekilerle AYNI OLMAMALI.
2. **DENGELİ OL:** Kullanıcının ana türlerine (örn: {genre_hint}) bağlı kal ve bu türlere uyan sürpriz sanatçılar öner.
3. **YORUM YAPMA:** Çıktın SADECE istenen JSON formatında olmalı.

**İSTENEN ÇIKIŞ FORMATI (Sadece bu JSON'u döndür):**
```json
{{
  "songs": [
    {{"artist": "Sanatçı Adı 1", "track": "Şarkı Adı 1"}},
    {{"artist": "Sanatçı Adı 2", "track": "Şarkı Adı 2"}},
    ...
    {{"artist": "Sanatçı Adı {config.GEMINI_PLAYLIST_REQUEST_SIZE}", "track": "Şarkı Adı {config.GEMINI_PLAYLIST_REQUEST_SIZE}"}}
  ]
}}
```

**Analiz edilecek veri:**
```json
{json_data}
```
"""
            
            logger.info(f"Generating personalized playlist: {playlist_name}")
            
            json_generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.5
            )

            response = self.model.generate_content(
                prompt,
                generation_config=json_generation_config
            )

            if not response.parts:
                logger.warning(f"Playlist generation blocked: {response.prompt_feedback}")
                st.error(f"❌ Liste oluşturma engellendi: {response.prompt_feedback}")
                return None, None

            json_text = response.text
            
            # Validate JSON structure
            try:
                Playlist.model_validate_json(json_text)
                
                usage = response.usage_metadata
                usage_metrics = {
                    "prompt_tokens": usage.prompt_token_count,
                    "response_tokens": usage.candidates_token_count,
                    "total_tokens": usage.total_token_count
                }
                
                logger.info(f"Generated playlist: {usage_metrics['total_tokens']} tokens")
                return json_text, usage_metrics

            except ValidationError as e:
                logger.error(f"Invalid JSON structure from Gemini: {e}")
                st.error(f"❌ Gemini'den gelen JSON yapısı bozuk!")
                st.code(json_text)
                return None, None
                
        except Exception as e:
            logger.error(f"Error generating playlist: {e}")
            st.error(f"❌ Kişiselleştirilmiş liste oluşturulurken hata: {e}")
            st.code(traceback.format_exc())
            return None, None

# ========================================
# UI DISPLAY FUNCTIONS (ENHANCED)
# ========================================

def display_spotify_report(report_data: Dict):
    """Display Spotify report with enhanced visualization"""
    
    # --- MOOD PROFILE VE AUDIO FEATURES BÖLÜMLERİ SİLİNDİ ---
    
    st.divider()
    
    # Genre Analysis
    if report_data.get('genres'):
        st.header("🎭 Müzik Profili: Türler ve Popülerlik") # Yeni başlık
        
        genres_data = report_data['genres']
        if genres_data:
            genres_df = pd.DataFrame(
                list(genres_data.items())[:10], 
                columns=['Tür', 'Sayı']
            )
            
            st.bar_chart(genres_df.set_index('Tür'), height=400)
            
            with st.expander("🎭 Türlere Göre Sanatçılar"):
                for genre, count in list(genres_data.items())[:15]:
                    artists = report_data.get('genre_by_artist', {}).get(genre, [])
                    if artists:
                        st.markdown(f"**{genre.title()}** ({count} tekrar): {', '.join(list(artists)[:5])}")

    st.divider()

    # Artists and Tracks
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("🎤 En İyi Sanatçılar")
        if report_data.get('top_artists'):
            artists_df = pd.DataFrame(report_data['top_artists'])
            
            display_df = artists_df[['name', 'popularity', 'followers']].copy()
            display_df.columns = ['Sanatçı', 'Popülerlik', 'Takipçi']
            
            st.dataframe(
                display_df, 
                use_container_width=True,
                hide_index=True
            )
    
    with col2:
        st.header("🏆 En İyi Şarkılar")
        if report_data.get('top_tracks'):
            tracks_df = pd.DataFrame(report_data['top_tracks'])
            
            display_df = tracks_df.copy()
            display_df['artists'] = display_df['artists'].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)
            display_df.columns = ['Şarkı', 'Sanatçı(lar)', 'Albüm']
            
            st.dataframe(
                display_df, 
                use_container_width=True,
                hide_index=True
            )

    st.divider()

    # Popularity and Decade Analysis
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("📈 Popülerlik Analizi")
        if report_data.get('popularity_stats'):
            stats = report_data['popularity_stats']
            
            avg_pop = stats.get('avg', 0)
            st.metric("Ortalama Popülerlik", f"{avg_pop:.1f} / 100")
            
            if avg_pop > 70:
                st.info("💡 **Mainstream** müzikleri seviyorsunuz! Popüler şarkıları takip ediyorsunuz.")
            elif avg_pop < 40:
                st.info("💡 **Underground** müzikleri tercih ediyorsunuz! Keşfetmeyi seviyorsunuz.")
            else:
                st.info("💡 **Dengeli** bir zevkiniz var! Hem popüler hem niche şarkılar dinliyorsunuz.")
            
            with st.expander("📊 Detaylı İstatistikler"):
                st.write(f"**En Yüksek:** {stats.get('max', 0)}")
                st.write(f"**En Düşük:** {stats.get('min', 0)}")
                st.write(f"**Ortanca:** {stats.get('median', 0):.1f}")
    
    with col2:
        st.header("📅 Yıllara Göre Dağılım")
        if report_data.get('decade_distribution'):
            decades_data = report_data['decade_distribution']
            
            if decades_data:
                decades_df = pd.DataFrame(
                    sorted(decades_data.items()), 
                    columns=['Yıl', 'Sayı']
                )
                st.bar_chart(decades_df.set_index('Yıl'), height=300)
                
                try:
                    oldest_decade = min([int(d.replace("'ler", "")) for d in decades_data.keys()])
                    if oldest_decade < 2000:
                        st.info(f"🕰️ Nostaljik bir ruh! {oldest_decade}'lerden müzik dinliyorsunuz.")
                except Exception as e:
                    logger.warning(f"Could not parse decades: {e}")

    st.divider()

    # Summary Statistics
    st.header("📊 Özet İstatistikler")
    if report_data.get('statistics'):
        stats = report_data['statistics']
        
        analysis_title = report_data.get('time_range', 'Bu Analizdeki')
        
        if "Kütüphanem" in analysis_title:
            metric_label = "🎵 Kütüphanedeki Şarkılar"
        elif "Çalma Listesi" in analysis_title:
            metric_label = "🎶 Playlist'teki Şarkılar"
        elif "Gerçek 'Tüm Şarkılar'" in analysis_title:
            metric_label = "🌟 EŞSİZ TOPLAM ŞARKI"
        else:
            metric_label = "💿 Analiz Edilen Şarkılar"
        
        cols = st.columns(4)
        
        cols[0].metric(
            metric_label, 
            f"{stats.get('analyzed_tracks', 0):,}",
            help="Bu analizde işlenen şarkı sayısı"
        )
        
        cols[1].metric(
            "🎸 Farklı Tür", 
            stats.get('unique_genres', 0),
            help="Keşfedilen müzik türü sayısı"
        )
        
        cols[2].metric(
            "👨‍🎤 Farklı Sanatçı", 
            stats.get('unique_artists', 0),
            help="Dinlenen sanatçı sayısı"
        )
        
        cols[3].metric(
            "❤️ Beğenilen Şarkı", 
            f"{stats.get('total_library_saved_tracks', 0):,}",
            help="Spotify kütüphanenizde kayıtlı toplam şarkı"
        )

def create_spotify_playlist(
    analyzer: SpotifyAdvancedAnalyzer, 
    playlist_name: str, 
    playlist_json: str
):
    """
    Create Spotify playlist from Gemini recommendations
    Enhanced with 2-phase search and better error handling
    """
    try:
        data = json.loads(playlist_json)
        songs_to_search = data.get('songs', [])
        
        if not songs_to_search:
            st.error("❌ Önerilen şarkı listesi boş.")
            return
        
        track_uris = []
        songs_found_count = 0
        not_found_songs = []
        
        # Search for tracks
        with st.spinner(f"🔍 Spotify'da {len(songs_to_search)} şarkı arasında en iyi {config.PLAYLIST_TARGET_SIZE} eşleşme aranıyor..."):
            progress_bar = st.progress(0, text="Arama başlıyor...")
            
            for i, song in enumerate(songs_to_search):
                
                # Stop if we found enough tracks
                if songs_found_count >= config.PLAYLIST_TARGET_SIZE:
                    logger.info(f"Target of {config.PLAYLIST_TARGET_SIZE} tracks reached")
                    break
                
                track_uri = None
                artist_name = song.get('artist', 'Unknown')
                track_name = song.get('track', 'Unknown')
                
                # Phase 1: Specific search
                try:
                    query_specific = f'track:"{track_name}" artist:"{artist_name}"'
                    results_specific = analyzer.sp.search(q=query_specific, type='track', limit=1)
                    
                    if results_specific['tracks']['items']:
                        track_uri = results_specific['tracks']['items'][0]['uri']
                        logger.debug(f"Found (specific): {track_name} - {artist_name}")
                        
                except Exception as e:
                    logger.debug(f"Specific search failed for {track_name}: {e}")

                # Phase 2: General search (if phase 1 failed)
                if not track_uri:
                    try:
                        query_general = f"{artist_name} {track_name}"
                        results_general = analyzer.sp.search(q=query_general, type='track', limit=1)
                        
                        if results_general['tracks']['items']:
                            track_uri = results_general['tracks']['items'][0]['uri']
                            logger.debug(f"Found (general): {track_name} - {artist_name}")
                            
                    except Exception as e:
                        logger.debug(f"General search failed for {track_name}: {e}")

                # Result
                if track_uri:
                    track_uris.append(track_uri)
                    songs_found_count += 1
                    progress_bar.progress(
                        (i + 1) / len(songs_to_search), 
                        text=f"✅ Bulundu ({songs_found_count}/{config.PLAYLIST_TARGET_SIZE}): {track_name}"
                    )
                else:
                    not_found_songs.append(f"{track_name} - {artist_name}")
                    progress_bar.progress(
                        (i + 1) / len(songs_to_search), 
                        text=f"⚠️ Bulunamadı: {track_name}"
                    )
            
            progress_bar.empty()
        
        if not track_uris:
            st.error("❌ Listeye eklenecek geçerli şarkı bulunamadı.")
            return

        # Create playlist
        with st.spinner(f"📝 '{playlist_name}' listesi {songs_found_count} şarkı ile oluşturuluyor..."):
            playlist = analyzer.sp.user_playlist_create(
                user=analyzer.user_id,
                name=playlist_name,
                public=True,
                description=f"Gemini AI ve Spotify Analiz Aracı tarafından {datetime.now().strftime('%d.%m.%Y')} tarihinde oluşturuldu."
            )
            
            # Add tracks to playlist
            analyzer.sp.playlist_add_items(playlist['id'], track_uris)
        
        logger.info(f"Playlist created: {playlist_name} with {songs_found_count} tracks")
        
        st.success(f"✅ Çalma listesi '{playlist_name}' başarıyla oluşturuldu! ({songs_found_count} şarkı eklendi)")
        st.markdown(f"**🎵 Listenizi açmak için tıklayın:** [Spotify'da Aç]({playlist['external_urls']['spotify']})")
        
        # Show not found songs
        if not_found_songs and len(not_found_songs) < 10:
            with st.expander(f"⚠️ Bulunamayan Şarkılar ({len(not_found_songs)})"):
                for song in not_found_songs:
                    st.text(f"• {song}")

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from Gemini: {e}")
        st.error("❌ Gemini'den gelen yanıt JSON formatında değil.")
        st.code(playlist_json)
        
    except Exception as e:
        logger.error(f"Error creating playlist: {e}")
        st.error(f"❌ Çalma listesi oluşturulurken hata: {e}")
        st.code(traceback.format_exc())

# ========================================
# MAIN STREAMLIT APP (ENHANCED)
# ========================================

def main():
    """Main application entry point"""
    
    # Page configuration
    st.set_page_config(
        page_title="Spotify Analiz Aracı - Enterprise",
        layout="wide",
        page_icon="🎵",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for better UI
    st.markdown("""
        <style>
        .main > div {padding-top: 2rem;}
        .stMetric {background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem;}
        </style>
    """, unsafe_allow_html=True)
    
    # ========================================
    # INITIALIZATION
    # ========================================
    
    # Load API keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
    SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

    if not all([GEMINI_API_KEY, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET]):
        st.error("❌ HATA: API Anahtarları ortam değişkenlerinde bulunamadı.")
        st.info("Lütfen GEMINI_API_KEY, SPOTIPY_CLIENT_ID ve SPOTIPY_CLIENT_SECRET değişkenlerini ayarlayın.")
        st.stop()
    
    # Initialize analyzers (cached)
    @st.cache_resource
    def init_spotify_analyzer():
        try:
            return SpotifyAdvancedAnalyzer(
                client_id=SPOTIPY_CLIENT_ID,
                client_secret=SPOTIPY_CLIENT_SECRET,
                redirect_uri=config.REDIRECT_URI
            )
        except Exception as e:
            logger.error(f"Spotify initialization failed: {e}")
            st.error(f"❌ Spotify'a bağlanılamadı: {e}")
            st.info(f"Redirect URI kontrol edin: {config.REDIRECT_URI}")
            st.stop()

    @st.cache_resource
    def init_gemini_analyzer(api_key: str):
        return GeminiReportAnalyzer(api_key=api_key)

    @st.cache_data(ttl=600, show_spinner="Çalma listeleriniz yükleniyor...")
    def load_user_playlists(_analyzer):
        return _analyzer.get_user_playlists()

    # ========================================
    # UI HEADER
    # ========================================
    
    st.title("🎵 Spotify Gelişmiş Müzik Analiz Aracı 🤖")
    st.markdown("**Enterprise Edition** - Müzik zevkinizi Spotify verileriyle analiz edin ve Gemini AI ile kişiselleştirilmiş yorumlar alın.")
    
    # Initialize analyzers
    try:
        analyzer = init_spotify_analyzer()
        gemini_analyzer = init_gemini_analyzer(GEMINI_API_KEY)
        st.sidebar.success(f"👤 Hoş geldin, **{analyzer.user_name}**! ✅")
    except Exception as e:
        st.error("Bağlantı hatası. Lütfen sayfayı yenileyin.")
        st.stop()

    # ========================================
    # SIDEBAR CONTROLS
    # ========================================
    
    st.sidebar.header("1️⃣ Analiz Kaynağı Seçin")

    analysis_source = st.sidebar.radio(
        "Neyi analiz etmek istiyorsunuz?",
        (
            "🔥 En Çok Dinlediklerim (Top 50)",
            "❤️ Kütüphane (Beğenilenler)",
            "📁 Bir Çalma Listem",
            "⚠️ Gerçek 'Tüm Şarkılar' (Yavaş)"
        ),
        key="analysis_source"
    )

    st.sidebar.header("2️⃣ Ayarlar")

    # Initialize variables
    selected_range = None
    selected_playlist_id = None
    report_title = ""
    tracks_to_analyze = []
    top_artists_data = None

    # Configure based on source
    if analysis_source == "🔥 En Çok Dinlediklerim (Top 50)":
        time_range_options = {
            '🕐 Son 4 Hafta': 'short_term',
            '📅 Son 6 Ay': 'medium_term',
            '⏳ Tüm Zamanlar': 'long_term'
        }
        
        selected_label = st.sidebar.selectbox(
            "Hangi dönemi analiz etmek istersiniz?",
            time_range_options.keys()
        )
        selected_range = time_range_options[selected_label]
        report_title = f"{selected_label} (En Çok Dinlenenler)"
        
    elif analysis_source == "❤️ Kütüphane (Beğenilenler)":
        report_title = "Kütüphanemizdeki Şarkılar (Beğenilenler)"
        st.sidebar.info("💡 Spotify'da beğendiğiniz tüm şarkılar analiz edilecek.")

    elif analysis_source == "📁 Bir Çalma Listem":
        try:
            playlists = load_user_playlists(analyzer)
            
            if not playlists:
                st.sidebar.warning("⚠️ Çalma listeniz bulunamadı.")
            else:
                playlist_map = {p['name']: p['id'] for p in playlists if p.get('name')}
                
                selected_playlist_name = st.sidebar.selectbox(
                    "Hangi çalma listeniz analiz edilsin?",
                    playlist_map.keys()
                )
                selected_playlist_id = playlist_map.get(selected_playlist_name)
                report_title = f"Çalma Listesi: {selected_playlist_name}"
                
        except Exception as e:
            logger.error(f"Error loading playlists: {e}")
            st.sidebar.error(f"Çalma listeleri çekilirken hata: {e}")

    elif analysis_source == "⚠️ Gerçek 'Tüm Şarkılar' (Yavaş)":
        st.sidebar.warning(
            "⚠️ **UYARI:** Bu analiz TÜM çalma listelerinizi ve beğenilen şarkılarınızı tarayacaktır. "
            "API limitlerine bağlı olarak dakikalar sürebilir.",
            icon="⏳"
        )
        report_title = "Gerçek 'Tüm Şarkılar' Analizi (Kütüphane + Tüm Listeler)"

    # Playlist name input
    st.sidebar.header("3️⃣ Keşif Listesi Adı")
    playlist_name = st.sidebar.text_input(
        "Yeni keşif listesi için ad:",
        f"Gemini Keşif: {report_title[:30]}",
        help="Gemini AI tarafından oluşturulacak playlist adı"
    )

    # ========================================
    # ANALYSIS TRIGGER
    # ========================================
    
    if st.sidebar.button("🚀 Analizi Başlat!", type="primary", use_container_width=True):
        
        # Clear previous session state
        for key in ['report_data', 'insights_text', 'usage_metrics', 'playlist_json', 'playlist_metrics']:
            if key in st.session_state:
                del st.session_state[key]
        
        try:
            # Phase 1: Fetch Spotify data
            st.info(f"📊 Analiz kaynağı: **{report_title}**")
            
            if analysis_source == "🔥 En Çok Dinlediklerim (Top 50)":
                with st.spinner("En çok dinlenenler çekiliyor..."):
                    tracks_to_analyze, top_artists_data = analyzer.get_top_tracks_and_artists(selected_range)
            
            elif analysis_source == "❤️ Kütüphane (Beğenilenler)":
                tracks_to_analyze = analyzer.get_all_saved_tracks()
            
            elif analysis_source == "📁 Bir Çalma Listem":
                if selected_playlist_id:
                    tracks_to_analyze = analyzer.get_playlist_tracks(selected_playlist_id)
                else:
                    st.error("❌ Geçerli bir çalma listesi seçilmedi.")
                    st.stop()

            elif analysis_source == "⚠️ Gerçek 'Tüm Şarkılar' (Yavaş)":
                tracks_to_analyze = analyzer.get_all_user_tracks_heavy()

            if not tracks_to_analyze:
                st.error("❌ Analiz edilecek şarkı bulunamadı. Kütüphaneniz veya listeniz boş olabilir.")
                st.stop()

            # Phase 2: Run core analysis
            with st.spinner(f"🔍 Analiz ediliyor: {len(tracks_to_analyze)} öğe işleniyor..."):
                report_data = analyzer.run_analysis_on_tracklist(
                    tracks_to_analyze, 
                    report_title, 
                    top_artists_data
                )
            
            if report_data is None:
                st.error("❌ Analiz tamamlanamadı.")
                st.stop()
                
            st.session_state['report_data'] = report_data
            
            # Save JSON report
            filename = f'spotify_detayli_rapor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Report saved to {filename}")

            # Phase 3: Generate Gemini insights
            with st.spinner("🤖 Gemini, müzik profilinizi analiz ediyor..."):
                insights_text, usage_metrics = gemini_analyzer.generate_insights(report_data)
                st.session_state['insights_text'] = insights_text
                st.session_state['usage_metrics'] = usage_metrics

            # Phase 4: Generate Gemini playlist
            with st.spinner("🎶 Gemini, kişiselleştirilmiş keşif listenizi oluşturuyor..."):
                playlist_json, playlist_metrics = gemini_analyzer.generate_personalized_playlist(
                    report_data, 
                    playlist_name
                )
                st.session_state['playlist_json'] = playlist_json
                st.session_state['playlist_metrics'] = playlist_metrics

            st.success("🎉 Raporunuz hazır! Aşağıya kaydırarak görebilirsiniz.")
            st.balloons()

        except Exception as e:
            logger.error(f"Analysis failed: {e}\n{traceback.format_exc()}")
            st.error(f"❌ Rapor oluşturulurken bir hata oluştu: {e}")
            with st.expander("🔍 Hata Detayları"):
                st.code(traceback.format_exc())

    # ========================================
    # DISPLAY RESULTS
    # ========================================
    
    st.divider()

    # 1. Spotify Report
    if 'report_data' in st.session_state:
        st.header(f"📊 Spotify Raporu: {st.session_state['report_data']['time_range']}")
        display_spotify_report(st.session_state['report_data'])
    else:
        st.info("👈 Lütfen sol taraftaki menüden bir analiz kaynağı seçip '🚀 Analizi Başlat' butonuna basın.")

    # 2. Gemini Insights
    if 'insights_text' in st.session_state:
        st.divider()
        st.header("✨ Gemini'den Gelen Müzik Profili Analizi")
        
        if st.session_state['insights_text']:
            st.markdown(st.session_state['insights_text'])
        else:
            st.warning("Analiz metni oluşturulamadı.")
        
        # Display token usage
        if 'usage_metrics' in st.session_state and st.session_state['usage_metrics']:
            with st.expander("📊 Gemini Kullanım Metrikleri (Analiz)"):
                st.json(st.session_state['usage_metrics'])

    # 3. Gemini Playlist
    if 'playlist_json' in st.session_state and st.session_state['playlist_json']:
        st.divider()
        st.header(f"🎶 Gemini Keşif Listesi: {playlist_name}")
        
        try:
            # Parse the JSON string from session state
            playlist_data = json.loads(st.session_state['playlist_json'])
            songs_list = playlist_data.get('songs', [])
            
            if songs_list:
                # Display the recommended songs
                playlist_df = pd.DataFrame(songs_list)
                playlist_df.columns = ['Sanatçı', 'Şarkı']
                st.dataframe(
                    playlist_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Add the create button
                if st.button("Bu Listeyi Spotify'da Oluştur 🚀", type="primary", use_container_width=True):
                    create_spotify_playlist(
                        analyzer, 
                        playlist_name, 
                        st.session_state['playlist_json']
                    )
            else:
                st.warning("Gemini bu analiz için bir şarkı listesi öneremedi.")

            # Display playlist token usage
            if 'playlist_metrics' in st.session_state and st.session_state['playlist_metrics']:
                with st.expander("📊 Gemini Kullanım Metrikleri (Liste Oluşturma)"):
                    st.json(st.session_state['playlist_metrics'])

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode playlist JSON from Gemini: {e}")
            st.error("❌ Gemini'den gelen çalma listesi yanıtı JSON formatında değildi.")
            st.code(st.session_state['playlist_json'])
        except Exception as e:
            logger.error(f"Error displaying playlist: {e}")
            st.error(f"Çalma listesi gösterilirken hata oluştu: {e}")

# ========================================
# APPLICATION ENTRY POINT
# ========================================

if __name__ == "__main__":
    main()