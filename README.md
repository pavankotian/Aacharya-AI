# Aacharya AI: Multilingual Public Health Assistant 

**Aacharya AI** is a Generative AI-powered solution designed to bridge the gap between rural communities and public health systems. It features a **multilingual chatbot** that provides medically accurate answers in local languages (Hindi/Kannada) and a **secure dashboard** for health workers to manage inventory and broadcast alerts.

---

##  Key Features

###  For Public Users (The Chatbot)
* **Multilingual Support:** Asks questions and receives answers in **English, Hindi, and Kannada**.
* **Voice-First Interface:** Integrated **Speech-to-Text** and **Text-to-Speech** for accessibility (perfect for users with low literacy).
* **RAG-Powered Accuracy:** Uses **Retrieval-Augmented Generation (RAG)** to fetch answers *only* from verified medical protocols (PDFs), ensuring safety.
* **Live Stock Updates:** Users can ask "Is Paracetamol available?" and get real-time answers from the inventory database.

###  For Health Workers (The Dashboard)
* **Secure Login:** Protected via **JWT Authentication**.
* **Inventory Management:** Add, update, or remove medical supplies in real-time.
* **Alert Broadcasting:** Send urgent health alerts (e.g., "Vaccination Camp on Sunday") that immediately appear on the public user's screen.

---

##  Tech Stack

### **Backend (API & Logic)**
* **Framework:** Python, FastAPI
* **Database:** SQLModel, SQLite
* **Authentication:** JWT (JSON Web Tokens), Bcrypt
* **Concurrency:** Asyncio (Non-blocking AI calls)

### **AI & Machine Learning**
* **LLM:** Google Gemini 2.5 Flash
* **RAG Pipeline:** LangChain
* **Vector Store:** ChromaDB (Local vector database)
* **Embeddings:** Hugging Face (Sentence Transformers)

### **Frontend (UI/UX)**
* **Library:** React.js
* **Styling:** Tailwind CSS
* **Accessibility:** Web Speech API (Native Browser Support)
* **HTTP Client:** Axios

---

##  Installation & Setup

Follow these steps to run the project locally.

### 1. Clone the Repository
```bash
git clone [https://github.com/YOUR_USERNAME/aacharya-ai-hackathon.git](https://github.com/YOUR_USERNAME/aacharya-ai-hackathon.git)
cd aacharya-ai-hackathon
2. Backend Setup
Navigate to the backend folder:

Bash
cd backend
Create a virtual environment:

Bash
python -m venv venv
Activate the environment:

Windows: .\venv\Scripts\activate

Mac/Linux: source venv/bin/activate

Install dependencies:

Bash
pip install fastapi uvicorn sqlmodel google-generativeai langchain langchain-community chromadb sentence-transformers python-jose passlib[bcrypt] python-multipart
Create a .env file in the backend folder and add your keys:

GOOGLE_API_KEY=your_gemini_api_key_here
SECRET_KEY=your_jwt_secret_key
Run the server:

Bash
uvicorn auth:app --reload
3. Frontend Setup
Open a new terminal and navigate to the frontend folder:

Bash
cd frontend
Install dependencies:

Bash
npm install
# OR
yarn install
Start the React app:

Bash
npm start
# OR
yarn start
```

## Usage Guide
Public Chat: Go to http://localhost:3000. Click the microphone icon to speak in Hindi or type your medical question.

Worker Login: Click "Health Worker Login" at the top right.

Default Credentials: (You can register a new user via the API docs at http://localhost:8000/docs)

Dashboard: Once logged in, use the tabs to update stock levels or post new alerts.

## Contributors
Akshay Kumar Singh - Backend Architecture, AI/RAG Integration, Database Design

Saurav Vats - Frontend Development, UI/UX, Accessibility Features

Pavan Kotian - Data Engineering, Prompt Engineering

Ayan Goel - Full Stack Integration, Documentation

Built for Hack-a-bot 2025.
