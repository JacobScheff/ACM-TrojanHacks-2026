# 🏥 AI Medical Scribe + Verifier  
Full-Stack React + Flask Application

## 📖 Overview

This project is a prototype web application for an **Automatic AI Medical Scribe + Verifier** system.

The system allows users to:

- Input a medical conversation transcript
- Generate a structured SOAP note
- Receive verification warnings
- View confidence scoring

This is an early-stage MVP and not intended for real clinical use.

---

## 🏗 Tech Stack

**Frontend**
- React (Vite)
- Axios

**Backend**
- Flask
- Flask-CORS
- Python 3.9+

---

## 📁 Project Structure

medical-scribe-ai/
│
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   └── venv/
│
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/

---

## ⚙️ Requirements

Make sure you have installed:

- Python 3.9 or higher
- Node.js 18 or higher
- npm
- Git (optional)

Check versions:

```bash
python --version
node -v
npm -v
```

---

# 🚀 Running the Application

You must run the backend and frontend separately in two terminals.

---

# 1️⃣ Start the Backend (Flask)

### Step 1: Navigate to backend folder

```bash
cd backend
```

### Step 2: Create virtual environment

Mac/Linux:

```bash
python -m venv venv
source venv/bin/activate
```

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run the server

```bash
python app.py
```

Backend will run at:

http://localhost:5000

---

# 2️⃣ Start the Frontend (React)

Open a new terminal window.

### Step 1: Navigate to frontend folder

```bash
cd frontend
```

### Step 2: Install dependencies

```bash
npm install
```

### Step 3: Start development server

```bash
npm run dev
```

You should see something like:

Local: http://localhost:5173/

Open that URL in your browser.

---

# 🧠 How It Works (MVP Version)

1. User pastes a transcript into the text area.
2. Frontend sends a POST request to:

```
POST /generate-note
```

3. Backend returns:
   - Generated SOAP note
   - Confidence score
   - Warning messages

4. Frontend displays results.

---

# ⚠️ Important Disclaimer

This is a prototype only.

- ❌ Not HIPAA compliant  
- ❌ Not FDA approved  
- ❌ Not for real patient data  
- ❌ Not production ready  

Do not upload real medical information.

---

# 🔧 Troubleshooting

### Frontend not loading?
Make sure backend is running first.

### Port 5173 already in use?

```bash
npm run dev -- --port 3000
```

### CORS errors?
Ensure `flask-cors` is installed and enabled in `app.py`.

---

# 👨‍💻 Hackathon Project

Built for ACM TrojanHacks 2026.
