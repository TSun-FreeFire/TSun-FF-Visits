<!-- Header Banner -->
<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:2E3192,100:1BFFFF&height=200&section=header&text=TSun%20FF%20Visits&fontSize=45&fontColor=fff&animation=fadeIn&fontAlignY=35"/>
</p>

<p align="center">
  <b>⚡ Flask-Based API for Sending Visits to Free Fire Profiles ⚡</b><br>
  <i>Async • Token-Managed • Protobuf Powered</i>
</p>

---
<div align="center">

## 📊 Badges & Stats
  <img src="https://img.shields.io/github/stars/TSun-FreeFire/TSun-FreeFire-Visits?color=yellow&style=for-the-badge"/>
  <img src="https://img.shields.io/github/forks/TSun-FreeFire/TSun-FreeFire-Visits?color=brightgreen&style=for-the-badge"/>
  <img src="https://img.shields.io/github/issues/TSun-FreeFire/TSun-FreeFire-Visits?color=orange&style=for-the-badge"/>
  <img src="https://img.shields.io/github/license/TSun-FreeFire/TSun-FreeFire-Visits?color=blue&style=for-the-badge"/>
</div>

<div align="center">

  <img src="https://github-readme-stats.vercel.app/api/pin/?username=TSun-FreeFire&repo=TSun-FreeFire-Visits&theme=tokyonight&hide_border=true"/>
</div>

---
<div align="center">

## 🚀 Features
</div>

✅ **Asynchronous Visit Sending**  
✅ **Token Management**  
✅ **Protobuf Parsing**   
✅ **Batch Processing**   
✅ **Docker & Vercel Ready**

---
<div align="center">

## 🛠️ Tech Stack

  <img src="https://img.shields.io/badge/Python-3.7+-blue?style=for-the-badge&logo=python"/>
  <img src="https://img.shields.io/badge/Flask-API-orange?style=for-the-badge&logo=flask"/>
  <img src="https://img.shields.io/badge/Protobuf-Parser-yellow?style=for-the-badge&logo=google"/>
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker"/>
  <img src="https://img.shields.io/badge/Vercel-Deployment-black?style=for-the-badge&logo=vercel"/>
</div>

---
<div align="center">

# 🧩 Installation
</div>

```bash
git clone https://github.com/TSun-FreeFire/TSun-FreeFire-Visits.git
cd TSun-FreeFire-Visits
pip install -r requirements.txt
````

### 🌍 Environment Variable

Set the URL for your token JSONs:

```bash
TOKEN_BASE_URL="https://raw.githubusercontent.com/TSun-FreeFire/TSun-FF-Visits/refs/heads/main/token_bd.json"
```

*(Replace with your own token File. it's Only For Example.)*

---

## 🧠 Usage

Run the Flask API:

```bash
python app.py
```

> API will start at: **[http://0.0.0.0:5000](http://0.0.0.0:5000)**

### Example Request:

```bash
http://localhost:5000/BD/123456789
```

#### Example Response:

```json
{
  "nickname": "PlayerOne",
  "level": 45,
  "likes": 320,
  "region": "BD",
  "uid": "123456789",
  "visits_success": 50,
  "visits_failed": 0
}
```

---

## 📁 Project Structure

```
TSun-FF-Visits
├── app.py                # Flask main app
├── byte.py               # Encryption utilities
├── protobuf_parser.py    # Protobuf decoding logic
├── visit_count_pb2.py    # Auto-generated protobuf classes
├── requirements.txt      # Python dependencies
├── Dockerfile            # Docker setup
├── vercel.json           # Vercel configuration
└── static/
    └── favicon.ico
```

---

## 🔐 Token File Format

```json
[
  {
    "token": "eyJhbGciOiJIUzI..."
  },
  {
    "token": "eyJhbGciOiJIUzI1Ni..."
  }
]
```

---

## 🤝 Contributing

Contributions are always welcome!

1. Fork this repository
2. Create a new branch (`feature/YourFeature`)
3. Commit changes
4. Open a Pull Request

> Have ideas or issues? [Open one here](https://github.com/TSun-FreeFire/TSun-FreeFire-Visits/issues)

---

## 📞 Connect with Us

<p align="center">
  <a href="https://t.me/saeedxdie"><img src="https://img.shields.io/badge/Telegram-TSun-blue?style=for-the-badge&logo=telegram"/></a>
  <a href="https://twitter.com/@saeedxdie"><img src="https://img.shields.io/badge/Twitter-TSun-black?style=for-the-badge&logo=x"/></a>
  <a href="https://instagram.com/saeedxdie"><img src="https://img.shields.io/badge/Instagram-Saeedxdie-DD2A7B?style=for-the-badge&logo=instagram"/></a>
  <a href="https://tiktok.com/saeedxdie"><img src="https://img.shields.io/badge/TikTok-Saeedxdie-000000?style=for-the-badge&logo=tiktok"/></a>
</p>

---

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:1BFFFF,100:2E3192&height=120&section=footer"/>
</p>

<p align="center"><b>⭐ Made with ❤️ by TSun Studio</b></p>