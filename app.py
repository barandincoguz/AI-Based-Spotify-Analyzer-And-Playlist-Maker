import streamlit as st
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from collections import Counter, defaultdict
import json
from datetime import datetime
import os
from typing import Dict, List, Tuple
import statistics
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import traceback
from pydantic import BaseModel, ValidationError
# -------------------------------------------------------------------
# SINIF 1: SPOTIFY ANALİZ ARACI (DÜZENLENDİ)
# -------------------------------------------------------------------

class SpotifyAdvancedAnalyzer:
    def __init__(self, client_id, client_secret, redirect_uri):
        """Gelişmiş Spotify API analiz aracı (Streamlit için düzenlendi)"""
        cache_path = ".spotify_cache"
        # YENİ İZİN EKLENDİ: 'playlist-modify-public'
        self.scope = "user-top-read playlist-read-private user-read-recently-played user-library-read playlist-modify-public"
        
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=self.scope,
            cache_path=cache_path,
            open_browser=True,
            show_dialog=True # Tarayıcıda onayı göstermeye zorla
        ))
        
        try:
            self.user_id = self.sp.current_user()['id']
            self.user_name = self.sp.current_user()['display_name']
        except Exception as e:
            st.error(f"Spotify bağlantı hatası: {e}")
            st.stop()

    # --- Veri Çekme Fonksiyonları (Değişiklik yok) ---
    def get_top_tracks(self, time_range='short_term', limit=50):
        return self.sp.current_user_top_tracks(time_range=time_range, limit=limit)['items']
    
    def get_top_artists(self, time_range='short_term', limit=50):
        return self.sp.current_user_top_artists(time_range=time_range, limit=limit)['items']
    
    def get_recently_played(self, limit=50):
        return self.sp.current_user_recently_played(limit=limit)['items']
    
    def get_saved_tracks_count(self):
        try:
            return self.sp.current_user_saved_tracks(limit=1)['total']
        except: return 0
    
    def get_audio_features(self, track_ids):
        """Şarkıların ses özelliklerini al"""
        try:
            features = self.sp.audio_features(track_ids)
            return [f for f in features if f is not None]
        except Exception as e:
            # Hatayı artık sessizce geçmiyoruz!
            print(f"HATA (get_audio_features): {e}")
            st.error(f"Spotify'dan ses özellikleri alınırken bir hata oluştu: {e}")
            return [] # Hata durumunda boş liste döndürmeye devam et

    # --- Analiz Fonksiyonları (Değişiklik yok) ---
    def analyze_audio_features(self, tracks):
        track_ids = [track['id'] for track in tracks if track.get('id')]
        if not track_ids: return None
        all_features = []
        for i in range(0, len(track_ids), 50):
            batch = track_ids[i:i+50]
            all_features.extend(self.get_audio_features(batch))
        if not all_features: return None
        metrics = {'danceability': [], 'energy': [], 'valence': [], 'acousticness': [], 'instrumentalness': [], 'speechiness': [], 'tempo': []}
        for feature in all_features:
            for key in metrics.keys():
                if feature.get(key) is not None:
                    metrics[key].append(feature[key])
        averages = {}
        for key, values in metrics.items():
            if values:
                averages[key] = statistics.mean(values)
        return averages
    
    def analyze_genres(self, tracks):
        genre_counter = Counter()
        artist_counter = Counter()
        genre_by_artist = defaultdict(set)
        for track in tracks:
            track_obj = track.get('track', track)
            for artist in track_obj.get('artists', []):
                artist_name = artist['name']
                artist_counter[artist_name] += 1
                try:
                    artist_info = self.sp.artist(artist['id'])
                    genres = artist_info.get('genres', [])
                    for genre in genres:
                        genre_counter[genre] += 1
                        genre_by_artist[genre].add(artist_name)
                except: pass
        return genre_counter, artist_counter, genre_by_artist
    
    def analyze_popularity(self, tracks):
        popularities = [track.get('track', track).get('popularity', 0) for track in tracks if track.get('track', track).get('popularity')]
        if not popularities: return None
        return {'avg': statistics.mean(popularities), 'max': max(popularities), 'min': min(popularities), 'median': statistics.median(popularities)}
    
    def get_decade_distribution(self, tracks):
        decades = Counter()
        for track in tracks:
            track_obj = track.get('track', track)
            release_date = track_obj.get('album', {}).get('release_date', '')
            if release_date:
                try:
                    year = int(release_date[:4])
                    decade = (year // 10) * 10
                    decades[f"{decade}'ler"] += 1
                except: pass
        return decades
    
    def create_mood_profile(self, audio_features):
        if not audio_features: return None
        energy = audio_features.get('energy', 0)
        valence = audio_features.get('valence', 0)
        danceability = audio_features.get('danceability', 0)
        if energy > 0.7 and danceability > 0.7: return "Enerjik ve Dans Edilebilir 🎉"
        elif valence > 0.7: return "Neşeli ve Pozitif 😊"
        elif energy < 0.4 and valence < 0.4: return "Sakin ve Melankolik 🌙"
        elif energy > 0.6 and valence < 0.5: return "Yoğun ve Duygusal 🔥"
        else: return "Dengeli ve Çeşitli 🎵"

    # --- ANA RAPOR FONKSİYONU (TÜM 'PRINT'LER SİLİNDİ) ---
    def fetch_spotify_data(self, time_range='short_term'):
        """
        Sessizce tüm Spotify verilerini toplar ve tek bir sözlükte döndürür.
        """
        # Veri toplama
        top_tracks = self.get_top_tracks(time_range, limit=50)
        top_artists = self.get_top_artists(time_range, limit=50)
        recent_tracks = self.get_recently_played(limit=50)
        genre_counter, artist_counter, genre_by_artist = self.analyze_genres(top_tracks)
        audio_features = self.analyze_audio_features(top_tracks)
        
        # Ek analizler
        popularity_stats = self.analyze_popularity(top_tracks)
        decade_dist = self.get_decade_distribution(top_tracks)
        mood_profile = self.create_mood_profile(audio_features)
        saved_count = self.get_saved_tracks_count()
        
        # JSON raporu (Veri döndürme)
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'time_range': time_range,
            'user': self.user_name,
            'mood_profile': mood_profile,
            'audio_features': audio_features,
            'genres': dict(genre_counter.most_common(20)),
            'genre_by_artist': {k: list(v) for k, v in genre_by_artist.items()},
            'top_artists': [{'name': a['name'], 'popularity': a.get('popularity', 0), 'followers': a.get('followers', {}).get('total', 0), 'genres': a.get('genres', [])} for a in top_artists[:20]],
            'top_tracks': [{'name': t['name'], 'artists': [a['name'] for a in t['artists']], 'album': t['album']['name']} for t in top_tracks[:20]],
            'popularity_stats': popularity_stats,
            'decade_distribution': dict(decade_dist),
            'statistics': {
                'saved_tracks': saved_count,
                'unique_genres': len(genre_counter),
                'unique_artists': len(top_artists),
                'analyzed_tracks': len(top_tracks),
                'recent_tracks': len(recent_tracks)
            }
        }
        return report_data
    
# -------------------------------------------------------------------
# PYDANTIC MODELLERİ (YAPISAL ÇIKTI İÇİN)
# -------------------------------------------------------------------

class Song(BaseModel):
    artist: str
    track: str

class Playlist(BaseModel):
    songs: List[Song]

# -------------------------------------------------------------------
# SINIF 2: GEMINI ANALİZ ARACI (DÜZENLENDİ)
# -------------------------------------------------------------------

class GeminiReportAnalyzer:
    def __init__(self, api_key):
        try:
            genai.configure(api_key=api_key)
            generation_config = {"temperature": 0.2}
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
        except Exception as e:
            st.error(f"❌ Gemini modeli başlatılırken hata oluştu: {e}")
            self.model = None

    def generate_insights(self, report_data: dict):
        if not self.model: return None, None
        json_data = json.dumps(report_data, ensure_ascii=False, indent=2)
        prompt = f"""
        Sen bir müzik psikoloğu ve uzman bir veri analistisin. Görevin, bir kullanıcının Spotify dinleme alışkanlıkları hakkında sana verilen JSON verilerini analiz etmek ve bu verilere dayanarak samimi, akıcı ve anlayışlı bir dille bir "müzik profili" çıkarmaktır. Verileri YORUMLA.
        Lütfen aşağıdaki yapıya benzer bir analiz yap:
        1.  **Giriş (Genel Müzik Viben):** Kullanıcının genel müzik zevkini (mood_profile, energy, valence) özetleyerek başla.
        2.  **Tür Analizi:** En çok dinlenen türlere bak. Bu türler kullanıcının kişiliği hakkında ne söylüyor olabilir?
        3.  **Sanatçı ve Popülerlik:** Top sanatçılara ve popülerlik istatistiklerine bak. Kullanıcı popüler (mainstream) mi, yoksa daha az bilinen (niche/underground) sanatçıları mı keşfetmeyi seviyor?
        4.  **Duygu Durumu (Audio Features):** Dans edilebilirlik, enerji, valens (pozitiflik) ve akustiklik verilerini yorumla.
        5.  **Zaman Yolculuğu (Decade Distribution):** Hangi on yıldan müzik dinlediği onun nostaljik mi yoksa yenilikçi mi olduğunu gösteriyor?
        6.  **Kapanış ve Öneri:** Tüm bu bilgilere dayanarak kullanıcıya kısa bir özet ve belki bir müzik önerisi sun.
        İşte analiz edilecek veri:
        ```json
        {json_data}
        ```
        Şimdi, bu verilere dayanarak akıcı bir metin halinde analizini oluştur:
        """
        try:
            response = self.chat.send_message(prompt)
            if response.parts:
                text_output = response.text
                usage = response.usage_metadata
                usage_metrics = {"prompt_tokens": usage.prompt_token_count, "response_tokens": usage.candidates_token_count, "total_tokens": usage.total_token_count}
                return text_output, usage_metrics
            else:
                st.error(f"❌ Gemini Yanıtı Engellendi! Sebep: {response.prompt_feedback}")
                return "Analiz, içerik filtrelemesi nedeniyle engellendi.", None
        except Exception as e:
            st.error(f"❌ Gemini analizi sırasında bir hata oluştu: {e}")
            return None, None
    
    
    def generate_personalized_playlist(self, report_data: dict, playlist_name: str = "Önerilen Müzik Listem"):
        """
        Kullanıcı rapor verisine dayanarak kişiselleştirilmiş bir müzik listesi oluşturur.
        Bu metod, modeli 'application/json' çıktısı vermeye zorlar ve Pydantic ile doğrular.
        """
        if not self.model:
            return None, None

        json_data = json.dumps(report_data, ensure_ascii=False, indent=2)
        
        prompt = f"""
            Sen, Spotify'ın "Haftalık Keşif" (Discover Weekly) listelerini tasarlayan uzman bir müzik veri bilimcisi ve küratörsün. Görevin, bir kullanıcının dinleme verilerini (JSON) analiz edip, onun *henüz keşfetmediği* ama müzik zevkine (türler, ses özellikleri, sanatçılar) dayanarak seveceği şarkıları bulmaktır.
            
            **GÖREV:**
            Aşağıdaki `{json_data}` verilerini analiz et. Bu analize dayanarak, '{playlist_name}' adını verdiğimiz liste için **15 ADET** şarkı öner. (Bazıları bulunamayabilir, o yüzden 10'dan fazla öner.)
    
            **KRİTİK KURALLAR:**
            1.  **YENİLİKÇİ OL:** Önerdiğin şarkılar, kullanıcının `top_artists` veya `top_tracks` listesindekilerle **AYNI OLMAMALI**.
            2.  **DENGELİ OL:** Kullanıcının ana türlerine (örn: {list(report_data.get('genres', {}).keys())[0:2]}) bağlı kal, ama aynı zamanda ses özelliklerine uyan sürpriz türlerden de 1-2 şarkı ekle.
            3.  **YORUM YAPMA:** Çıktın SADECE istenen JSON formatında olmalı.
    
            **İSTENEN ÇIKIŞ FORMATI (Sadece bu JSON'u döndür):**
            ```json
            {{
              "songs": [
                {{"artist": "Sanatçı Adı 1", "track": "Şarkı Adı 1"}},
                {{"artist": "Sanatçı Adı 2", "track": "Şarkı Adı 2"}},
                {{"artist": "Sanatçı Adı 3", "track": "Şarkı Adı 3"}},
                {{"artist": "Sanatçı Adı 4", "track": "Şarkı Adı 4"}},
                {{"artist": "Sanatçı Adı 5", "track": "Şarkı Adı 5"}},
                {{"artist": "Sanatçı Adı 6", "track": "Şarkı Adı 6"}},
                {{"artist": "Sanatçı Adı 7", "track": "Şarkı Adı 7"}},
                {{"artist": "Sanatçı Adı 8", "track": "Şarkı Adı 8"}},
                {{"artist": "Sanatçı Adı 9", "track": "Şarkı Adı 9"}},
                {{"artist": "Sanatçı Adı 10", "track": "Şarkı Adı 10"}},
                {{"artist": "Sanatçı Adı 11", "track": "Şarkı Adı 11"}},
                {{"artist": "Sanatçı Adı 12", "track": "Şarkı Adı 12"}},
                {{"artist": "Sanatçı Adı 13", "track": "Şarkı Adı 13"}},
                {{"artist": "Sanatçı Adı 14", "track": "Şarkı Adı 14"}},
                {{"artist": "Sanatçı Adı 15", "track": "Şarkı Adı 15"}}
              ]
            }}
            ```
        """
        
        try:
            print("\n🧠 Gemini, 15 şarkılık kişiselleştirilmiş müzik listesini oluşturuyor (JSON modu)...")
            
            json_generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.2
            )

            response = self.model.generate_content(
                prompt,
                generation_config=json_generation_config
            )

            if not response.parts:
                st.error(f"❌ Liste oluşturma engellendi: {response.prompt_feedback}")
                return None, None

            json_text = response.text
            
            try:
                Playlist.model_validate_json(json_text)
                
                usage = response.usage_metadata
                usage_metrics = {"prompt_tokens": usage.prompt_token_count, "response_tokens": usage.candidates_token_count, "total_tokens": usage.total_token_count}
                
                return json_text, usage_metrics

            except ValidationError as e:
                st.error(f"❌ Gemini'den gelen JSON yapısı bozuk! Hata: {e}")
                st.code(json_text)
                return None, None
                
        except Exception as e:
            st.error(f"❌ Kişiselleştirilmiş liste oluşturulurken kritik hata oluştu: {e}")
            st.code(traceback.format_exc())
            return None, None

# -------------------------------------------------------------------
# STREAMLIT ARAYÜZÜ İÇİN YARDIMCI FONKSİYONLAR
# -------------------------------------------------------------------

def display_spotify_report(report_data):
    """Streamlit arayüzünde Spotify verilerini görselleştirir"""
    
    st.header("🎭 Müzik Profiliniz")
    st.subheader(f"✨ Müzik Tarzınız: {report_data.get('mood_profile', 'N/A')}")

    if report_data.get('audio_features'):
        features = report_data['audio_features']
        cols = st.columns(3)
        cols[0].metric("⚡ Enerji", f"{features.get('energy', 0)*100:.0f}%")
        cols[1].metric("💃 Dans Edilebilirlik", f"{features.get('danceability', 0)*100:.0f}%")
        cols[2].metric("😊 Pozitiflik (Valence)", f"{features.get('valence', 0)*100:.0f}%")
        
        with st.expander("Tüm Ses Özelliklerini Gör"):
            cols = st.columns(2)
            cols[0].metric("🎸 Akustik Oran", f"{features.get('acousticness', 0)*100:.0f}%")
            cols[1].metric("🎹 Enstrümantal Oran", f"{features.get('instrumentalness', 0)*100:.0f}%")
            cols[0].metric("🎤 Konuşma İçeriği", f"{features.get('speechiness', 0)*100:.0f}%")
            cols[1].metric("🥁 Ortalama Tempo", f"{features.get('tempo', 0):.0f} BPM")

    st.divider()
    
    # Tür Analizi
    if report_data.get('genres'):
        st.header("🎸 En Çok Dinlediğiniz Türler (Top 10)")
        genres_df = pd.DataFrame(report_data['genres'].items(), columns=['Tür', 'Sayı']).head(10)
        st.bar_chart(genres_df.set_index('Tür'))
        
        with st.expander("Türlere Göre Sanatçılar"):
            for genre, count in report_data['genres'].items():
                artists = report_data.get('genre_by_artist', {}).get(genre, [])
                st.markdown(f"**{genre.title()}** ({count} tekrar): {', '.join(artists[:3])}")

    st.divider()

    # Sanatçı ve Şarkı Listeleri
    col1, col2 = st.columns(2)
    with col1:
        st.header("🎤 En İyiler: Sanatçılar")
        if report_data.get('top_artists'):
            artists_df = pd.DataFrame(report_data['top_artists'])
            st.dataframe(artists_df[['name', 'popularity', 'followers']], use_container_width=True)
    
    with col2:
        st.header("🏆 En İyiler: Şarkılar")
        if report_data.get('top_tracks'):
            tracks_df = pd.DataFrame(report_data['top_tracks'])
            st.dataframe(tracks_df, use_container_width=True)

    st.divider()

    # Popülerlik ve Yıllara Göre Dağılım
    col1, col2 = st.columns(2)
    with col1:
        st.header("📈 Popülerlik Analizi")
        if report_data.get('popularity_stats'):
            stats = report_data['popularity_stats']
            st.metric("Ortalama Popülerlik", f"{stats.get('avg', 0):.1f} / 100")
            if stats.get('avg', 0) > 70:
                st.info("💡 Mainstream müzikleri seviyorsunuz!")
            elif stats.get('avg', 0) < 40:
                st.info("💡 Daha underground müzikleri tercih ediyorsunuz!")
            else:
                st.info("💡 Dengeli bir zevkiniz var!")
    
    with col2:
        st.header("📅 Yıllara Göre Dağılım")
        if report_data.get('decade_distribution'):
            decades_df = pd.DataFrame(report_data['decade_distribution'].items(), columns=['Yıl', 'Sayı'])
            st.bar_chart(decades_df.set_index('Yıl'))

    st.divider()

    st.header("📊 Özet İstatistikler")
    if report_data.get('statistics'):
        stats = report_data['statistics']
        cols = st.columns(3)
        cols[0].metric("🎵 Kütüphanedeki Şarkılar", f"{stats.get('saved_tracks', 0):,}")
        cols[1].metric("🎸 Farklı Tür Sayısı", stats.get('unique_genres', 0))
        cols[2].metric("🎤 Farklı Sanatçı Sayısı", stats.get('unique_artists', 0))

def create_spotify_playlist(analyzer, playlist_name, playlist_json):
    """
    Gemini'den gelen JSON'u kullanarak Spotify'da çalma listesi oluşturur.
    2 Aşamalı Arama ve 10 şarkı hedefi ile güncellendi.
    """
    try:
        data = json.loads(playlist_json)
        # Gemini'den gelen 15 (veya daha fazla) şarkılık listeyi al
        songs_to_search = data.get('songs', [])
        if not songs_to_search:
            st.error("Önerilen şarkı listesi boş.")
            return

        track_uris = []
        songs_found_count = 0
        
        # --- YENİ ARAMA MANTIĞI ---
        with st.spinner(f"Spotify'da {len(songs_to_search)} şarkı arasında en iyi 10 eşleşme aranıyor..."):
            progress_bar = st.progress(0, text="Arama başlıyor...")
            
            for i, song in enumerate(songs_to_search):
                
                # HEDEF 1: 10 şarkıyı bulduysak, aramayı durdur
                if songs_found_count >= 10:
                    st.toast("Hedeflenen 10 şarkıya ulaşıldı.")
                    break
                
                track_uri = None
                
                # 1. DENEME: Birebir (Spesifik) Arama
                try:
                    query_specific = f"track:\"{song['track']}\" artist:\"{song['artist']}\""
                    results_specific = analyzer.sp.search(q=query_specific, type='track', limit=1)
                    if results_specific['tracks']['items']:
                        track_uri = results_specific['tracks']['items'][0]['uri']
                except Exception:
                    pass # Arama hatası olursa 2. denemeye geç

                # 2. DENEME: Genel (Fuzzy) Arama (Eğer ilki başarısızsa)
                if not track_uri:
                    try:
                        query_general = f"{song['artist']} {song['track']}"
                        results_general = analyzer.sp.search(q=query_general, type='track', limit=1)
                        if results_general['tracks']['items']:
                            track_uri = results_general['tracks']['items'][0]['uri']
                    except Exception:
                        pass # Bu da başarısız olursa atla

                # SONUÇ:
                if track_uri:
                    track_uris.append(track_uri)
                    songs_found_count += 1
                    progress_bar.progress((i + 1) / len(songs_to_search), text=f"✅ Bulundu ({songs_found_count}/10): {song['track']}")
                else:
                    progress_bar.progress((i + 1) / len(songs_to_search), text=f"⚠️ Bulunamadı: {song['track']}")
                    # Kullanıcı arayüzünü kirletmemek için bulunamayanları sessizce geç
                    # st.warning(f"Eşleşme bulunamadı: {song['track']} - {song['artist']}")
            
        # --- ARAMA MANTIĞI SONU ---
        
        if not track_uris:
            st.error("Listeye eklenecek geçerli şarkı bulunamadı.")
            return

        with st.spinner(f"'{playlist_name}' listesi {songs_found_count} şarkı ile oluşturuluyor..."):
            playlist = analyzer.sp.user_playlist_create(
                user=analyzer.user_id,
                name=playlist_name,
                public=True,
                description=f"Gemini AI ve Spotify Analiz Aracı tarafından {datetime.now().strftime('%d.%m.%Y')} tarihinde oluşturuldu."
            )
            
            # Şarkıları 100'lük gruplar halinde ekle (Spotify limiti)
            analyzer.sp.playlist_add_items(playlist['id'], track_uris)
        
        st.success(f"✅ Çalma listesi '{playlist_name}' başarıyla oluşturuldu! ({songs_found_count} şarkı eklendi)")
        st.markdown(f"**Listenizi açmak için tıklayın:** [{playlist['external_urls']['spotify']}]({playlist['external_urls']['spotify']})")

    except json.JSONDecodeError:
        st.error("❌ Gemini'den gelen yanıt JSON formatında değil. Ham çıktı:")
        st.code(playlist_json)
    except Exception as e:
        st.error(f"❌ Çalma listesi oluşturulurken bir hata oluştu: {e}")
        st.code(traceback.format_exc())

# -------------------------------------------------------------------
# ANA STREAMLIT UYGULAMASI
# -------------------------------------------------------------------

st.set_page_config(page_title="Spotify Analiz Aracı", layout="wide", page_icon="🎵")

# --- API Anahtarları ---
# Spotipy anahtarlarını ortam değişkenlerinden oku
# Spotipy kütüphanesi bu değişken isimlerini otomatik olarak tanır!
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = "http://127.0.0.1:8888/callback" # Spotify Dashboard'da aynen bu olmalı

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY or not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
    st.error("❌ HATA: API Anahtarları (GEMINI veya SPOTIPY) ortam değişkenlerinde bulunamadı.")
    st.info("Lütfen .zshrc dosyanızı kontrol edin.")
    st.stop()
# --- Bağlantıları Önbelleğe Alma ---

@st.cache_resource
def init_spotify_analyzer():
    try:
        analyzer = SpotifyAdvancedAnalyzer(
            client_id=SPOTIPY_CLIENT_ID, 
            client_secret=SPOTIPY_CLIENT_SECRET, 
            redirect_uri=REDIRECT_URI
        )
        return analyzer
    except Exception as e:
        st.error(f"❌ Spotify'a bağlanılamadı. Spotify Dashboard'da Redirect URI'yi kontrol edin: {REDIRECT_URI}")
        st.error(f"Hata detayı: {e}")
        st.stop()

@st.cache_resource
def init_gemini_analyzer(api_key):
    return GeminiReportAnalyzer(api_key=api_key)

# --- Arayüz Başlangıcı ---
st.title("🎵 Spotify Gelişmiş Müzik Analiz Aracı 🤖")
st.markdown("Müzik zevkinizi Spotify verileriyle analiz edin ve Gemini AI ile kişiselleştirilmiş yorumlar alın.")

try:
    analyzer = init_spotify_analyzer()
    gemini_analyzer = init_gemini_analyzer(GEMINI_API_KEY)
    st.sidebar.success(f"Hoş geldin, {analyzer.user_name}! ✅")
except Exception as e:
    st.error("Bağlantı hatası. Lütfen sayfayı yenileyin.")
    st.stop()

# --- Kenar Çubuğu (Sidebar) ---
st.sidebar.header("Rapor Ayarları")
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

playlist_name = st.sidebar.text_input("Yeni Çalma Listesi Adı:", f"Gemini Keşif Listem ({selected_label})")

if st.sidebar.button(f"🚀 {selected_label} Raporunu Oluştur", type="primary", use_container_width=True):
    # Tüm verileri temizle
    st.session_state.clear()
    
    try:
        # 1. Spotify Verilerini Çek
        with st.spinner("📥 Spotify verileri toplanıyor... (Bu işlem 10-15 sn sürebilir)"):
            report_data = analyzer.fetch_spotify_data(selected_range)
            st.session_state['report_data'] = report_data
            
            # JSON olarak kaydet (opsiyonel, sunucuda çalışır)
            filename = f'spotify_detayli_rapor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)

        # 2. Gemini Analizini Yap
        with st.spinner("🤖 Gemini, müzik profilinizi analiz ediyor..."):
            insights_text, usage_metrics = gemini_analyzer.generate_insights(report_data)
            st.session_state['insights_text'] = insights_text
            st.session_state['usage_metrics'] = usage_metrics

        # 3. Gemini Çalma Listesini Oluştur
        with st.spinner("🎶 Gemini, kişiselleştirilmiş keşif listenizi oluşturuyor..."):
            # --- DEĞİŞİKLİK BURADA ---
            playlist_json, playlist_metrics = gemini_analyzer.generate_personalized_playlist(report_data, playlist_name)
            st.session_state['playlist_json'] = playlist_json
            st.session_state['playlist_metrics'] = playlist_metrics # Metrikleri de kaydet
            # --- DEĞİŞİKLİK SONU ---

        st.success("🎉 Raporunuz hazır! Aşağı kaydırarak görebilirsiniz.")

    except Exception as e:
        st.error(f"❌ Rapor oluşturulurken bir hata oluştu: {e}")
        st.code(traceback.format_exc())

# --- Sonuçların Gösterilmesi ---
st.divider()

# 1. Spotify Raporunu Göster
if 'report_data' in st.session_state:
    st.header(f"📊 {selected_label} Spotify Raporu")
    display_spotify_report(st.session_state['report_data'])
else:
    st.info("Lütfen sol taraftaki menüden bir rapor oluşturun.")

# 2. Gemini Analizini Göster
if 'insights_text' in st.session_state:
    st.divider()
    st.header("✨ Gemini'den Gelen Müzik Profili Analizi")
    st.markdown(st.session_state['insights_text'])
    
    if 'usage_metrics' in st.session_state:
        with st.expander("📊 Gemini Kullanım Metrikleri (Analiz)"):
            st.json(st.session_state['usage_metrics'])

# 3. Gemini Çalma Listesini Göster
if 'playlist_json' in st.session_state:
    st.divider()
    st.header(f"🎶 Gemini Keşif Listesi: {playlist_name}")
    
    try:
        # st.json(st.session_state['playlist_json']) # Ham JSON'u görmek için
        playlist_data = json.loads(st.session_state['playlist_json'])
        st.dataframe(playlist_data.get('songs', []), use_container_width=True)
        
        # BONUS: Çalma Listesini Spotify'da Oluştur Butonu
        if st.button("Bu Listeyi Spotify'da Oluştur 🚀", type="primary", use_container_width=True):
            create_spotify_playlist(analyzer, playlist_name, st.session_state['playlist_json'])

        # --- YENİ EKLENEN BÖLÜM ---
        if 'playlist_metrics' in st.session_state:
            with st.expander("📊 Gemini Kullanım Metrikleri (Liste Oluşturma)"):
                st.json(st.session_state['playlist_metrics'])
        # --- YENİ BÖLÜM SONU ---

    except json.JSONDecodeError:
        st.error("❌ Gemini'den gelen çalma listesi yanıtı JSON formatında değil. Ham çıktı:")
        st.code(st.session_state['playlist_json'])