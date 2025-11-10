# 🎵 Spotify Gelişmiş Müzik Analiz Aracı 🤖

Bu proje, **Spotify verilerinizi derinlemesine analiz eden** ve **Google Gemini (2.5-Flash)** yapay zekasını kullanarak müzik zevkiniz hakkında kişiselleştirilmiş, psikolojik bir profil çıkaran interaktif bir web uygulamasıdır.

Sadece “en çok dinlenen” şarkılarınızı değil, tüm kütüphanenizi veya spesifik çalma listelerinizi analiz ederek, **müzik ruh halinizi**, **favori türlerinizi** ve **dinleme alışkanlıklarınızı** ortaya çıkarır.

> 💡

## ![alt text](<../../../../var/folders/g_/jlsd_6ln6pvdtskyr2f9hf3h0000gn/T/TemporaryItems/NSIRD_screencaptureui_bbwuUA/Ekran Resmi 2025-11-11 00.44.28.png>)

## ✨ Temel Özellikler

### 🎧 Çok Kaynaklı Analiz

- **En Çok Dinlediklerim:** Son 4 hafta, 6 ay veya tüm zamanlardaki top 50 şarkınızı analiz eder.
- **Kütüphane (Beğenilenler):** “Beğenilen Şarkılar” (❤️) listenizi inceler.
- **Çalma Listesi Analizi:** İstediğiniz çalma listesini (“Workout”, “Gece” vb.) analiz eder.
- **Gerçek “Tüm Şarkılar” (Yavaş):** Binlerce şarkıdan oluşan “Gerçek Müzik Evreni” profili çıkarır.

### 📊 Derinlemesine Veri Analizi

- **Ses Özellikleri:** Enerji, Dans Edilebilirlik, Pozitiflik (Valence), Akustiklik ve Tempo.
- **Tür Haritası:** En baskın türler ve kilit sanatçılar.
- **Zaman Yolculuğu:** Hangi on yıllara (örn: 80’ler, 2020’ler) odaklandığınız.
- **Popülerlik:** Mainstream mi yoksa underground mu?

### 🤖 Yapay Zeka Destekli Yorumlama (Google Gemini)

- **Kişiselleştirilmiş Profil:** Gemini AI, “müzik psikoloğu” rolüyle size özel analiz metni üretir.
- **Token Takibi:** Her analiz için harcanan token miktarını gösterir.

### 🎶 AI Destekli Çalma Listesi Oluşturma

- **Akıllı Öneri:** Profilinize uygun 15 yeni şarkı önerisi.
- **Sağlam Arama:** Spotify’da 2 aşamalı arama (spesifik + esnek).
- **Tek Tıkla Oluşturma:** 10 şarkıyı tek tıkla yeni çalma listesi haline getirir.

### 🔒 Güvenli ve Sağlam Tasarım

- **API Güvenliği:** `os.getenv` ile anahtarlar gizli tutulur.
- **Veri Doğrulama:** `Pydantic` ile JSON yapısı doğrulanır.
- **Veri Temizleme:** Spotify API’sinden gelen bozuk kayıtlar temizlenir.
- **Önbellekleme:** `@st.cache_resource`, `@st.cache_data` ile hız artırılır.

---

## 🛠️ Kullanılan Teknolojiler

| Teknoloji            | Açıklama               |
| -------------------- | ---------------------- |
| **Python 3.11+**     | Ana programlama dili   |
| **Streamlit**        | İnteraktif web arayüzü |
| **Spotipy**          | Spotify API bağlantısı |
| **Google Gemini AI** | Yapay zeka analizleri  |
| **Pandas**           | Veri işleme            |
| **Pydantic**         | Veri doğrulama         |

---

## 📦 Kurulum ve Çalıştırma

### 1️⃣ Proje Dosyaları

```bash
git clone https://github.com/barandincoguz/spotify-analyzer.git
cd spotify-analyzer
```

### 2️⃣ Gerekli Kütüphaneler

`requirements.txt` içeriği:

```txt
streamlit
pandas
spotipy
google-generativeai
pydantic
```

Kurulum:

```bash
pip install -r requirements.txt
```

### 3️⃣ API Anahtarlarının Yapılandırılması

Bu uygulama için **Spotify API** ve **Google Gemini API** anahtarlarına ihtiyacınız vardır.

#### 🔹 Spotify API

1. [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) → “Create App”
2. “Settings” → `Client ID` ve `Client Secret` değerlerini alın.
3. Redirect URI:  
   `http://127.0.0.1:8888/callback`

#### 🔹 Google Gemini API

1. [Google AI Studio](https://aistudio.google.com) → “Get API key”
2. `GEMINI_API_KEY` anahtarınızı alın.

#### 🔹 Ortam Değişkenleri

**macOS / Linux:**
(macOS için ./zshrc dosyasının içine aşağıdaki 3 env variable'ı kaydetmeniz gerekebilir)

```bash
export SPOTIPY_CLIENT_ID='SENİN_SPOTIFY_CLIENT_ID_BURAYA'
export SPOTIPY_CLIENT_SECRET='SENİN_SPOTIFY_SECRET_BURAYA'
export GEMINI_API_KEY='SENİN_GEMINI_API_KEY_BURAYA'
```

**Windows (CMD):**

```bash
setx SPOTIPY_CLIENT_ID "SENİN_SPOTIFY_CLIENT_ID_BURAYA"
setx SPOTIPY_CLIENT_SECRET "SENİN_SPOTIFY_SECRET_BURAYA"
setx GEMINI_API_KEY "SENİN_GEMINI_API_KEY_BURAYA"
```

> !Değişikliklerin geçerli olması için terminali yeniden başlatın.

---

### 4️⃣ Uygulamayı Çalıştırma

```bash
streamlit run app.py
```

Tarayıcıda otomatik olarak `http://localhost:8501` açılacaktır.

> 🔑 İlk çalıştırmada Spotify hesabınızla giriş yapmanız gerekebilir.

---

## 📜 Lisans

Bu proje **MIT Lisansı** altında lisanslanmıştır.  
Detaylar için `LICENSE` dosyasına bakın.
