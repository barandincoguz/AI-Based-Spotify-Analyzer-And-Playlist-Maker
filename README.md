# 🎵 Spotify Gelişmiş Müzik Analiz Aracı (Enterprise Edition) 🤖

# 🎵 Spotify Advanced Music Analyzer (Enterprise Edition) 🤖

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Framework-Streamlit-FF4B4B?logo=streamlit" alt="Streamlit">
  <img src="https://img.shields.io/badge/API-Google%20Gemini-orange?logo=google" alt="Gemini">
  <img src="https://img.shields.io/badge/API-Spotify-brightgreen?logo=spotify" alt="Spotify">
  <img src="https://img.shields.io/badge/License-Educational-lightgrey" alt="License">
</p>

---

## 🇹🇷 Açıklama

Spotify dinleme alışkanlıklarınızı analiz eden, tür/sanatçı/popülerlik ve dönem dağılımlarını çıkaran; Google Gemini AI entegrasyonu sayesinde kişisel müzik profili metni ve tarzınıza uygun keşif listeleri oluşturan bir **Streamlit uygulamasıdır**.

## 🇬🇧 Description

A Streamlit app that analyzes your Spotify listening habits (genres, artists, popularity, decades) and uses Google Gemini AI to generate a personalized music profile and discovery playlists.

---

## ✨ Özellikler / Features

**🇹🇷 Türkçe:**

- 🎧 Gelişmiş veri çekme: Beğenilenler, Top Tracks, Çalma Listeleri, Tüm Şarkılar
- 📊 Tür, sanatçı, popülerlik ve dönem bazlı istatistikler
- 🤖 Gemini entegrasyonu: kişisel müzik profili + akıllı keşif listesi
- 🧱 Kurumsal seviye yapı: önbellekleme, yeniden deneme, loglama, Pydantic doğrulama
- 💎 Streamlit ile modern grafiksel arayüz

**🇬🇧 English:**

- 🎧 Advanced data retrieval: liked songs, top tracks, playlists, full library
- 📊 Genre, artist, popularity, and decade-based analytics
- 🤖 Gemini-powered AI music profile and smart discovery playlist
- 🧱 Enterprise-grade architecture: caching, retrying, logging, Pydantic validation
- 💎 Modern Streamlit dashboard with interactive visuals

---

## 📦 Gereksinimler / Requirements

**🇹🇷**

- Python 3.9+
- Spotify Geliştirici hesabı (Client ID & Secret)
- Google Gemini API anahtarı
- Gerekli izinler:  
  `user-top-read, playlist-read-private, user-read-recently-played, user-library-read, playlist-modify-public`

**🇬🇧**

- Python 3.9+
- Spotify Developer Account (Client ID & Secret)
- Google Gemini API Key
- Required scopes:  
  `user-top-read, playlist-read-private, user-read-recently-played, user-library-read, playlist-modify-public`

---

## 🚀 Kurulum / Setup

### 1️⃣ Projeyi Klonlayın / Clone the Project

```bash
git clone https://github.com/your-username/SpotifyAnalyzer.git
cd SpotifyAnalyzer
```

### 2) Sanal Ortam / Virtualenv

```bash
# macOS / Linux (zsh)
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3) Bağımlılıkları yükleyin / Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Kimlik bilgilerini ayarlayın / Set credentials

🇹🇷 Spotify ve Gemini anahtarlarını ortam değişkeni olarak tanımlayın veya .env dosyası oluşturun.
🇬🇧 Set your Spotify and Gemini credentials as environment variables or create a .env file.

TR (zsh):

```bash
export SPOTIPY_CLIENT_ID="<your_client_id>"
export SPOTIPY_CLIENT_SECRET="<your_client_secret>"
export SPOTIPY_REDIRECT_URI="http://localhost:8888/callback"
export GEMINI_API_KEY="<your_gemini_api_key>"
```

EN (zsh):

```bash
export SPOTIPY_CLIENT_ID="<your_client_id>"
export SPOTIPY_CLIENT_SECRET="<your_client_secret>"
export SPOTIPY_REDIRECT_URI="http://localhost:8888/callback"
export GEMINI_API_KEY="<your_gemini_api_key>"
```

İpucu / Tip: Bir `.env` dosyası oluşturup shell’e yükleyebilirsiniz:

```bash
cat > .env << 'EOF'
SPOTIPY_CLIENT_ID=<your_client_id>
SPOTIPY_CLIENT_SECRET=<your_client_secret>
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
GEMINI_API_KEY=<your_gemini_api_key>
EOF

# zsh: .env içeriğini current shell'e aktar
set -a; source .env; set +a
```

Spotify Developer ayarlarında Redirect URI olarak `http://localhost:8888/callback` eklemeyi unutmayın.

---

## ▶️ Çalıştırma / Run

```bash
streamlit run appv2.py
```

🇹🇷 Tarayıcı otomatik açılmazsa terminalde yazan URL’yi kopyalayın.
🇬🇧 If your browser doesn’t open automatically, copy the local URL printed in the terminal.

---

## 🧭 Kullanım / Usage

🇹🇷

1. Sol menüden analiz kaynağı seçin:
   🔥 En Çok Dinlediklerim
   ❤️ Beğenilenler
   📁 Çalma Listesi
   ⚠️ Tüm Şarkılar (tüm kütüphane taraması)

2. Keşif listesi adı girin.

3. “Analizi Başlat!” butonuna basın.

4. Grafikler, istatistikler, Gemini profili ve öneriler ekranda görüntülenir.

5. Sonuç JSON raporu otomatik olarak kaydedilir (spotify_detayli_rapor_YYYYMMDD_HHMMSS.json).

🇬🇧

1. Choose your data source:
   🔥 Top Tracks
   ❤️ Liked Songs
   📁 Playlist
   ⚠️ All Songs (library-wide scan)

2. Enter the discovery playlist name.

3. Click “Start Analysis!”.

4. View charts, statistics, Gemini AI music profile, and recommendations.

5. A detailed JSON report is automatically saved (spotify_detailed_report_YYYYMMDD_HHMMSS.json).

---

## 🛠️ Sorun Giderme / Troubleshooting

🇹🇷

- Redirect URI mismatch: Spotify dashboard’da Redirect URI olarak `http://localhost:8888/callback` ekli olmalı.
- Giriş döngüsü / cache: `.spotify_cache` dosyasını silip tekrar deneyin.
- 429/Rate limit: Bir süre bekleyin; uygulama zaten yeniden deneme (retry) ve gecikme kullanır.
- Gemini hataları: API anahtarını ve kota durumunu kontrol edin. Bazı içerikler güvenlik filtresi nedeniyle engellenebilir.
- Streamlit sürümü: `st.cache_data` ve `st.cache_resource` için güncel bir sürüm kullanın (pip upgrade).
- Port meşgul: `streamlit run appv2.py --server.port 8502` gibi farklı port deneyin.
  🇬🇧
- Redirect URI mismatch → Check your Spotify Dashboard.
- Login loop → Delete .spotify_cache.
- 429 (Rate Limit) → Wait; auto-retry is enabled.
- Gemini error → Check your API key and quota.
- Port in use → Try --server.port 8502.

---

## 🔐 Gizlilik / Privacy

🇹🇷
Veriler sadece sizin Spotify hesabınızdan okunur ve yerelde işlenir. Oluşturulan playlist, açık veya gizli olarak hesabınızda oluşturulur (koda göre: public=True). İsterseniz sonradan gizliye alabilirsiniz.
🇬🇧
Data is read from your Spotify account and processed locally. The app creates a playlist on your account (public by default in code). You can make it private afterward.

---

## 🗺️ Yol Haritası / Roadmap (Öneri)

🇹🇷

- Streamlit secrets desteği (st.secrets) ile dağıtım kolaylığı
- Playlist-modify-private desteği ve “private playlist” seçeneği
- Daha gelişmiş hata mesajları ve metrikler

🇬🇧

- Audio feature visualizations (danceability, energy, valence)
- Streamlit secrets integration for deployment
- Support for private playlist creation
- Improved error messages and user metrics

---

## 📜 Lisans / License

🇹🇷
Bu proje eğitim ve kişisel kullanım amaçlıdır. Ticari kullanım veya dağıtım için lisans koşullarını belirleyin.
🇬🇧
This project is for educational and personal use. Define license terms for commercial use or redistribution.

<p align="center"> <sub>Developed by <b>Ahmet Baran Dincoğuz</b> | 2025 ©</sub> </p>
