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

class SpotifyAdvancedAnalyzer:
    def __init__(self, client_id, client_secret, redirect_uri):
        """Gelişmiş Spotify API analiz aracı"""
        cache_path = ".spotify_cache"
        self.scope = "user-top-read playlist-read-private user-read-recently-played user-library-read"
        
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=self.scope,
            cache_path=cache_path,
            open_browser=True,
            show_dialog=False
        ))
        
        # Renkli çıktı için ANSI kodları
        self.colors = {
            'header': '\033[95m',
            'blue': '\033[94m',
            'cyan': '\033[96m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'red': '\033[91m',
            'bold': '\033[1m',
            'underline': '\033[4m',
            'end': '\033[0m'
        }
    
    def print_colored(self, text, color='end', bold=False):
        """Renkli çıktı yazdır"""
        style = self.colors.get(color, self.colors['end'])
        if bold:
            style = self.colors['bold'] + style
        print(f"{style}{text}{self.colors['end']}")
    
    def get_top_tracks(self, time_range='short_term', limit=50):
        """En çok dinlenen şarkıları getir"""
        return self.sp.current_user_top_tracks(time_range=time_range, limit=limit)['items']
    
    def get_top_artists(self, time_range='short_term', limit=50):
        """En çok dinlenen sanatçıları getir"""
        return self.sp.current_user_top_artists(time_range=time_range, limit=limit)['items']
    
    def get_recently_played(self, limit=50):
        """Son dinlenen şarkıları getir"""
        return self.sp.current_user_recently_played(limit=limit)['items']
    
    def get_saved_tracks_count(self):
        """Kaydedilen şarkı sayısı"""
        try:
            return self.sp.current_user_saved_tracks(limit=1)['total']
        except:
            return 0
    
    def get_audio_features(self, track_ids):
        """Şarkıların ses özelliklerini al"""
        try:
            features = self.sp.audio_features(track_ids)
            return [f for f in features if f is not None]
        except:
            return []
    
    def analyze_audio_features(self, tracks):
        """Şarkıların ortalama özelliklerini analiz et"""
        track_ids = [track['id'] for track in tracks if track.get('id')]
        
        if not track_ids:
            return None
        
        # 50'şerli gruplara böl (API limiti)
        all_features = []
        for i in range(0, len(track_ids), 50):
            batch = track_ids[i:i+50]
            all_features.extend(self.get_audio_features(batch))
        
        if not all_features:
            return None
        
        # Ortalama değerleri hesapla
        metrics = {
            'danceability': [],
            'energy': [],
            'valence': [],  # Mutluluk
            'acousticness': [],
            'instrumentalness': [],
            'speechiness': [],
            'tempo': []
        }
        
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
        """Detaylı tür analizi"""
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
                except:
                    pass
        
        return genre_counter, artist_counter, genre_by_artist
    
    def analyze_popularity(self, tracks):
        """Popülerlik analizi"""
        popularities = []
        
        for track in tracks:
            track_obj = track.get('track', track)
            pop = track_obj.get('popularity', 0)
            if pop:
                popularities.append(pop)
        
        if not popularities:
            return None
        
        return {
            'avg': statistics.mean(popularities),
            'max': max(popularities),
            'min': min(popularities),
            'median': statistics.median(popularities)
        }
    
    def get_decade_distribution(self, tracks):
        """Şarkıların yıllara göre dağılımı"""
        decades = Counter()
        
        for track in tracks:
            track_obj = track.get('track', track)
            album = track_obj.get('album', {})
            release_date = album.get('release_date', '')
            
            if release_date:
                try:
                    year = int(release_date[:4])
                    decade = (year // 10) * 10
                    decades[f"{decade}'ler"] += 1
                except:
                    pass
        
        return decades
    
    def create_mood_profile(self, audio_features):
        """Müzik zevki profili oluştur"""
        if not audio_features:
            return None
        
        # Enerji profili
        energy = audio_features.get('energy', 0)
        valence = audio_features.get('valence', 0)
        danceability = audio_features.get('danceability', 0)
        
        # Müzik tarzı belirleme
        if energy > 0.7 and danceability > 0.7:
            mood = "Enerjik ve Dans Edilebilir 🎉"
        elif valence > 0.7:
            mood = "Neşeli ve Pozitif 😊"
        elif energy < 0.4 and valence < 0.4:
            mood = "Sakin ve Melankolik 🌙"
        elif energy > 0.6 and valence < 0.5:
            mood = "Yoğun ve Duygusal 🔥"
        else:
            mood = "Dengeli ve Çeşitli 🎵"
        
        return mood
    
    def print_progress_bar(self, current, total, prefix='', length=40):
        """İlerleme çubuğu göster"""
        percent = float(current) / float(total)
        filled = int(length * percent)
        bar = '█' * filled + '░' * (length - filled)
        print(f'\r{prefix} |{bar}| {percent:.1%}', end='', flush=True)
        if current == total:
            print()
    
    def generate_detailed_report(self, time_range='short_term'):
        """Detaylı ve görsel rapor oluştur"""
        time_labels = {
            'short_term': '🕐 Son 4 Hafta',
            'medium_term': '📅 Son 6 Ay',
            'long_term': '⏳ Tüm Zamanlar'
        }
        
        # Başlık
        os.system('clear' if os.name == 'posix' else 'cls')
        self.print_colored("\n" + "=" * 70, 'cyan', bold=True)
        self.print_colored("🎵 SPOTIFY GELİŞMİŞ MÜZİK ANALİZ RAPORU 🎵".center(70), 'header', bold=True)
        self.print_colored("=" * 70, 'cyan', bold=True)
        
        print(f"\n📊 Analiz Dönemi: {time_labels.get(time_range, time_range)}")
        print(f"🕒 Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y - %H:%M')}")
        print(f"👤 Kullanıcı: {self.sp.current_user()['display_name']}")
        
        # Veri toplama
        self.print_colored("\n\n📥 VERİLER TOPLANIYOR...", 'yellow', bold=True)
        
        print("\n→ En çok dinlenen şarkılar alınıyor...")
        top_tracks = self.get_top_tracks(time_range, limit=50)
        self.print_progress_bar(1, 5, 'İlerleme:', 50)
        
        print("→ En çok dinlenen sanatçılar alınıyor...")
        top_artists = self.get_top_artists(time_range, limit=50)
        self.print_progress_bar(2, 5, 'İlerleme:', 50)
        
        print("→ Son dinlenenler alınıyor...")
        recent_tracks = self.get_recently_played(limit=50)
        self.print_progress_bar(3, 5, 'İlerleme:', 50)
        
        print("→ Tür analizi yapılıyor...")
        genre_counter, artist_counter, genre_by_artist = self.analyze_genres(top_tracks)
        self.print_progress_bar(4, 5, 'İlerleme:', 50)
        
        print("→ Ses özellikleri analiz ediliyor...")
        audio_features = self.analyze_audio_features(top_tracks)
        self.print_progress_bar(5, 5, 'İlerleme:', 50)
        
        # Ek analizler
        popularity_stats = self.analyze_popularity(top_tracks)
        decade_dist = self.get_decade_distribution(top_tracks)
        mood_profile = self.create_mood_profile(audio_features)
        saved_count = self.get_saved_tracks_count()
        
        # RAPOR BAŞLIYOR
        print("\n")
        
        # 1. MÜZİK PROFİLİ
        self.print_colored("\n" + "=" * 70, 'cyan')
        self.print_colored("🎭 MÜZİK PROFİLİNİZ", 'header', bold=True)
        self.print_colored("=" * 70, 'cyan')
        
        if mood_profile:
            print(f"\n✨ Müzik Tarzınız: {mood_profile}")
        
        if audio_features:
            print("\n📊 Müzik Özellikleriniz:")
            
            features_display = {
                'energy': ('Enerji Seviyesi', '⚡'),
                'danceability': ('Dans Edilebilirlik', '💃'),
                'valence': ('Pozitiflik/Mutluluk', '😊'),
                'acousticness': ('Akustik Oran', '🎸'),
                'instrumentalness': ('Enstrümantal Oran', '🎹'),
                'speechiness': ('Konuşma İçeriği', '🎤')
            }
            
            for key, (label, emoji) in features_display.items():
                if key in audio_features:
                    value = audio_features[key]
                    percentage = int(value * 100)
                    bar_length = int(percentage / 2)
                    bar = '█' * bar_length + '░' * (50 - bar_length)
                    print(f"\n{emoji} {label:<25} |{bar}| {percentage}%")
            
            if 'tempo' in audio_features:
                tempo = audio_features['tempo']
                print(f"\n🥁 Ortalama Tempo: {tempo:.0f} BPM")
        
        # 2. EN ÇOK DİNLENEN TÜRLER
        self.print_colored("\n\n" + "=" * 70, 'cyan')
        self.print_colored("🎸 EN ÇOK DİNLEDİĞİNİZ TÜRLER", 'green', bold=True)
        self.print_colored("=" * 70, 'cyan')
        
        if genre_counter:
            total_genres = sum(genre_counter.values())
            
            for i, (genre, count) in enumerate(genre_counter.most_common(10), 1):
                percentage = (count / total_genres) * 100
                bar_length = int(percentage)
                bar = '█' * bar_length + '░' * (100 - bar_length)
                
                # En popüler sanatçıları göster
                artists = list(genre_by_artist[genre])[:3]
                artists_str = ", ".join(artists)
                
                print(f"\n{i:2d}. {genre.title():<30}")
                print(f"    |{bar}| {percentage:.1f}%")
                print(f"    👥 Sanatçılar: {artists_str}")
        else:
            print("\n⚠️  Tür bilgisi bulunamadı.")
        
        # 3. EN ÇOK DİNLENEN SANATÇILAR
        self.print_colored("\n\n" + "=" * 70, 'cyan')
        self.print_colored("🎤 EN ÇOK DİNLEDİĞİNİZ SANATÇILAR", 'blue', bold=True)
        self.print_colored("=" * 70, 'cyan')
        
        for i, artist in enumerate(top_artists[:15], 1):
            name = artist['name']
            popularity = artist.get('popularity', 0)
            followers = artist.get('followers', {}).get('total', 0)
            genres = ", ".join(artist.get('genres', [])[:2])
            
            pop_bar = '★' * (popularity // 10)
            
            if i <= 3:
                medals = ['🥇', '🥈', '🥉']
                print(f"\n{medals[i-1]} {i}. {name}")
            else:
                print(f"\n   {i:2d}. {name}")
            
            print(f"       Popülerlik: {pop_bar} ({popularity}/100)")
            if followers > 0:
                print(f"       Takipçi: {followers:,}")
            if genres:
                print(f"       Türler: {genres}")
        
        # 4. EN ÇOK DİNLENEN ŞARKILAR
        self.print_colored("\n\n" + "=" * 70, 'cyan')
        self.print_colored("🏆 EN ÇOK DİNLEDİĞİNİZ ŞARKILAR", 'yellow', bold=True)
        self.print_colored("=" * 70, 'cyan')
        
        for i, track in enumerate(top_tracks[:15], 1):
            name = track['name']
            artists = ", ".join([a['name'] for a in track['artists']])
            album = track['album']['name']
            duration_ms = track['duration_ms']
            duration_min = duration_ms // 60000
            duration_sec = (duration_ms % 60000) // 1000
            
            if i <= 3:
                medals = ['🥇', '🥈', '🥉']
                print(f"\n{medals[i-1]} {i}. {name}")
            else:
                print(f"\n   {i:2d}. {name}")
            
            print(f"       Sanatçı: {artists}")
            print(f"       Albüm: {album}")
            print(f"       Süre: {duration_min}:{duration_sec:02d}")
        
        # 5. YILLARA GÖRE DAĞILIM
        if decade_dist:
            self.print_colored("\n\n" + "=" * 70, 'cyan')
            self.print_colored("📅 YILLARA GÖRE MÜZİK TERCİHİNİZ", 'green', bold=True)
            self.print_colored("=" * 70, 'cyan')
            
            total_tracks = sum(decade_dist.values())
            for decade, count in sorted(decade_dist.items(), reverse=True):
                percentage = (count / total_tracks) * 100
                bar = '█' * int(percentage)
                print(f"\n{decade:<15} |{bar:<50}| {count} şarkı ({percentage:.1f}%)")
        
        # 6. POPÜLERLİK ANALİZİ
        if popularity_stats:
            self.print_colored("\n\n" + "=" * 70, 'cyan')
            self.print_colored("📈 POPÜLERLİK ANALİZİ", 'blue', bold=True)
            self.print_colored("=" * 70, 'cyan')
            
            print(f"\nOrtalama Popülerlik: {popularity_stats['avg']:.1f}/100")
            print(f"En Popüler Şarkı: {popularity_stats['max']}/100")
            print(f"En Az Popüler: {popularity_stats['min']}/100")
            print(f"Medyan: {popularity_stats['median']:.1f}/100")
            
            if popularity_stats['avg'] > 70:
                print("\n💡 Mainstream müzikleri seviyorsunuz!")
            elif popularity_stats['avg'] < 40:
                print("\n💡 Daha underground müzikleri tercih ediyorsunuz!")
            else:
                print("\n💡 Popüler ve alternatif arasında dengeli bir zevkiniz var!")
        
        # 7. ÖZET İSTATİSTİKLER
        self.print_colored("\n\n" + "=" * 70, 'cyan')
        self.print_colored("📊 ÖZET İSTATİSTİKLER", 'header', bold=True)
        self.print_colored("=" * 70, 'cyan')
        
        stats = [
            ("🎵 Kütüphanenizdeki Şarkı Sayısı", saved_count),
            ("🎸 Farklı Tür Sayısı", len(genre_counter)),
            ("🎤 Farklı Sanatçı Sayısı", len(top_artists)),
            ("🏆 Analiz Edilen Şarkı Sayısı", len(top_tracks)),
            ("⏱️  Son Dinlenen Şarkı Sayısı", len(recent_tracks))
        ]
        
        for label, value in stats:
            print(f"\n{label:<45} {value:>10,}")
        
        if genre_counter:
            dominant = genre_counter.most_common(1)[0]
            print(f"\n🎯 En Baskın Türünüz: {dominant[0].title()} ({dominant[1]} tekrar)")
        
        # Kapanış
        self.print_colored("\n\n" + "=" * 70, 'cyan', bold=True)
        self.print_colored("✨ RAPOR TAMAMLANDI ✨".center(70), 'green', bold=True)
        self.print_colored("=" * 70 + "\n", 'cyan', bold=True)
        
        # JSON raporu
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'time_range': time_range,
            'user': self.sp.current_user()['display_name'],
            'mood_profile': mood_profile,
            'audio_features': audio_features,
            'genres': dict(genre_counter.most_common(20)),
            'top_artists': [(a['name'], a.get('popularity', 0)) for a in top_artists[:20]],
            'top_tracks': [(t['name'], [a['name'] for a in t['artists']]) for t in top_tracks[:20]],
            'popularity_stats': popularity_stats,
            'decade_distribution': dict(decade_dist),
            'statistics': {
                'saved_tracks': saved_count,
                'unique_genres': len(genre_counter),
                'unique_artists': len(top_artists)
            }
        }
        
        return report_data


class GeminiReportAnalyzer:
    """
    Spotify rapor verilerini alıp Gemini ile analiz eden sınıf.
    """
    def __init__(self, api_key):
        """
        Gemini modelini API anahtarıyla başlatır.
        """
        try:
            genai.configure(api_key=api_key)
            generation_config = {
              "temperature": 0.1, 
            }
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
            print("✨ Gemini Analiz Modeli başarıyla başlatıldı.")
        except Exception as e:
            print(f"❌ Gemini başlatılırken hata oluştu: {e}")
            self.model = None

    def generate_insights(self, report_data: dict):
        """
        Verilen rapor verisini analiz eder ve doğal dil çıktısı ile
        kullanım metriklerini (token) döndürür.
        """
        if not self.model:
            return None, None # Metin ve metrikler için None döndür

        json_data = json.dumps(report_data, ensure_ascii=False, indent=2)
        
        prompt = f"""
        Sen bir müzik psikoloğu ve uzman bir veri analistisin. Görevin, bir kullanıcının Spotify dinleme alışkanlıkları hakkında sana verilen JSON verilerini analiz etmek ve bu verilere dayanarak samimi, akıcı ve anlayışlı bir dille bir "müzik profili" çıkarmaktır.

        Sadece verileri listeleme, verileri YORUMLA.

        Lütfen aşağıdaki yapıya benzer bir analiz yap:

        1.  **Giriş (Genel Müzik Viben):** Kullanıcının genel müzik zevkini (mood_profile, energy, valence) özetleyerek başla. (Örn: "Senin müzik ruhun hem enerjik... hem de melankolik...")
        2.  **Tür Analizi:** En çok dinlenen türlere bak. Bu türler kullanıcının kişiliği hakkında ne söylüyor olabilir? (Örn: "Rap ve elektronik ağırlığı, hızlı tempolu bir yaşamı sevdiğini gösteriyor...")
        3.  **Sanatçı ve Popülerlik:** Top sanatçılara ve popülerlik istatistiklerine bak. Kullanıcı popüler (mainstream) mi, yoksa daha az bilinen (niche/underground) sanatçıları mı keşfetmeyi seviyor? Bu onun karakteri hakkında ne ipucu verir?
        4.  **Duygu Durumu (Audio Features):** Dans edilebilirlik, enerji, valens (pozitiflik) ve akustiklik verilerini yorumla. Bu kişi daha çok hangi duygusal durumda müzik dinliyor?
        5.  **Zaman Yolculuğu (Decade Distribution):** Hangi on yıldan müzik dinlediği (örn: 80'ler veya 2020'ler) onun nostaljik mi yoksa yenilikçi mi olduğunu gösteriyor?
        6.  **Kapanış ve Öneri:** Tüm bu bilgilere dayanarak kullanıcıya kısa bir özet ve belki bir müzik önerisi sun.

        İşte analiz edilecek veri:
        ```json
        {json_data}
        ```

        Şimdi, bu verilere dayanarak akıcı bir metin halinde analizini oluştur:
        """

        try:
            print("\n🧠 Gemini, müzik raporunu analiz ediyor... (Bu işlem biraz sürebilir)")
            response = self.chat.send_message(prompt)
            
            # --- YENİ BÖLÜM: Metrikleri Çekme ---
            if response.parts:
                # 1. Analiz metnini al
                text_output = response.text
                
                # 2. Kullanım verisini (token) al
                usage = response.usage_metadata
                usage_metrics = {
                    "prompt_tokens": usage.prompt_token_count,
                    "response_tokens": usage.candidates_token_count,
                    "total_tokens": usage.total_token_count
                }
                
                # 3. İkisini birlikte döndür
                return text_output, usage_metrics
            else:
                # Güvenlik filtresi vb. nedeniyle engellendi
                print(f"❌ Gemini Yanıtı Engellendi! Sebep: {response.prompt_feedback}")
                return "Analiz, içerik filtrelemesi nedeniyle engellendi.", None
            # --- Değişiklik Sonu ---

        except Exception as e:
            print(f"❌ Gemini analizi sırasında bir hata oluştu: {e}")
            if 'response' in locals():
                print(f"Hata Detayı: {response.candidates}")
            return None, None # Hata durumunda None döndür
    def generate_personalized_playlist(self, report_data: dict, playlist_name: str = "Önerilen Müzik Listem"):
        """
        Kullanıcı rapor verisine dayanarak kişiselleştirilmiş bir müzik listesi oluşturur.
        """
        if not self.model:
            return None

        json_data = json.dumps(report_data, ensure_ascii=False, indent=2)
        
        prompt = f"""
        Sen bir müzik küratörüsün. Görevin, bir kullanıcının Spotify dinleme alışkanlıkları hakkında sana verilen JSON verilerine dayanarak, kullanıcının zevklerine uygun 10 şarkılık kişiselleştirilmiş bir müzik listesi oluşturmaktır.

        İşte analiz edilecek veri:
        ```json
        {json_data}
        ```

        Şimdi, bu verilere dayanarak '{playlist_name}' adlı müzik listesini oluştur:
        """

        try:
            print("\n🧠 Gemini, kişiselleştirilmiş müzik listesini oluşturuyor...")
            response = self.chat.send_message(prompt)
            return response.text
        except Exception as e:
            print(f"❌ Kişiselleştirilmiş liste oluşturulurken hata oluştu: {e}")
            return None
# ANA PROGRAM
if __name__ == "__main__":
    print("=" * 70)
    print("🎵 GELİŞMİŞ SPOTIFY MÜZİK ANALİZ ARACI 🎵".center(70))
    print("=" * 70)
    print("\n📝 Kurulum Adımları:")
    print("1. https://developer.spotify.com/dashboard")
    print("2. 'Create app' ile yeni uygulama oluşturun")
    print("3. Redirect URI: http://localhost:8888/callback")
    print("4. Client ID ve Client Secret'ı kopyalayın\n")
    
    CLIENT_ID = "d8e0da89b31f481fa134d9235e519765"
    CLIENT_SECRET = "fcfbbf035089409cb5ef34f05694243f"
    REDIRECT_URI = "http://127.0.0.1:8888/callback"  # Dashboard'da AYNEN bu şekilde olmalı
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("❌ HATA: GEMINI_API_KEY ortam değişkeni bulunamadı.")
        print("Lütfen API key'inizi 'GEMINI_API_KEY' adıyla ortam değişkeni olarak ayarlayın.")
        exit()
    
    if CLIENT_ID == "your_client_id_here" or CLIENT_SECRET == "your_client_secret_here":
        print("❌ HATA: CLIENT_ID ve CLIENT_SECRET değerlerini girin!")
        exit()
    
    try:
        print("\n🔐 Spotify'a bağlanılıyor...")
        analyzer = SpotifyAdvancedAnalyzer(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
        print("✅ Bağlantı başarılı!\n")
        
        print("=" * 70)
        print("Hangi dönemi analiz etmek istersiniz?\n")
        print("1. 🕐 Son 4 hafta (Güncel müzik zevkiniz)")
        print("2. 📅 Son 6 ay (Orta vadeli tercihleriniz)")
        print("3. ⏳ Tüm zamanlar (Genel müzik profiliniz)")
        print("=" * 70)
        
        choice = input("\nSeçiminiz (1/2/3) [Enter = 1]: ").strip() or "1"
        
        time_ranges = {"1": "short_term", "2": "medium_term", "3": "long_term"}
        selected_range = time_ranges.get(choice, "short_term")
        
        report_data = analyzer.generate_detailed_report(time_range=selected_range)
        
        filename = f'spotify_detayli_rapor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Detaylı rapor '{filename}' dosyasına kaydedildi.\n")
        
        # 3. YENİ BÖLÜM: Gemini ile Analiz
        if GEMINI_API_KEY and report_data:
            print("\n" + "=" * 70)
            print("🤖 GEMINI İLE DERİN ANALİZ BAŞLIYOR 🤖".center(70))
            print("=" * 70)

            gemini_analyzer = GeminiReportAnalyzer(api_key=GEMINI_API_KEY)
            
            # --- DEĞİŞİKLİK BURADA ---
            # Artık iki değer alıyoruz: metin ve metrikler
            insights_text, usage_metrics = gemini_analyzer.generate_insights(report_data)
            suggested_playlist = gemini_analyzer.generate_personalized_playlist(report_data)

            if insights_text:
                print("\n" + "*" * 70)
                print("✨ Gemini'den Gelen Müzik Profili Analizin ✨".center(70))
                print("*" * 70 + "\n")
                print(insights_text) # Analiz metnini yazdır
                print("\n" + "*" * 70)
                
                # --- YENİ BÖLÜM: Metrikleri Yazdırma ---
                if usage_metrics:
                    print("\n" + "=" * 70)
                    print("📊 GEMINI KULLANIM METRİKLERİ 📊".center(70))
                    print("=" * 70)
                    print(f"Giriş (Prompt) Token Sayısı   : {usage_metrics['prompt_tokens']}")
                    print(f"Çıkış (Response) Token Sayısı : {usage_metrics['response_tokens']}")
                    print("---------------------------------".center(70))
                    print(f"TOPLAM TOKEN SAYISI           : {usage_metrics['total_tokens']}")
                    print("=" * 70)
                # --- Değişiklik Sonu ---

            # --- DEĞİŞİKLİK SONU ---
            
        else:
            if not GEMINI_API_KEY:
                print("\n⚠️ Gemini API Key bulunmadığı için derin analiz atlandı.")
            if not report_data:
                 print("\n⚠️ Rapor verisi boş olduğu için derin analiz atlandı.")
        if suggested_playlist:
            print("\n" + "=" * 70)
            print("🎶 Gemini'den Gelen Kişiselleştirilmiş Müzik Listesi 🎶".center(70))
            print("=" * 70 + "\n")
            print(suggested_playlist)
            print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ Ana programda bir hata oluştu: {e}")
        import traceback
        traceback.print_exc()