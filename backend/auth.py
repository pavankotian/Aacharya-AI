import os
from pathlib import Path
import logging
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import asyncio # <-- 1. ADDED THIS IMPORT

# --- CRITICAL FIX: CONSOLIDATED SQLMODEL IMPORTS ---
# These must be imported first because they are used immediately below for Database Setup and Models.
from sqlmodel import SQLModel, Field, create_engine, Session, select, delete
# ----------------------------------------------------

from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai

# --- AUTH IMPORTS ---
from passlib.context import CryptContext
from jose import JWTError, jwt
# --------------------


logger = logging.getLogger(__name__)

# --- RAG Imports and Setup (Kept for completeness, though these are defined in rag_setup.py) ---
# NOTE: This block is usually separated into models.py and rag_setup.py, but is kept here based on your file structure.

# Database Setup
ROOT_DIR = Path(__file__).parent
DATABASE_URL = f"sqlite:///{ROOT_DIR}/health_chatbot.db"
# This line now works because create_engine is imported above
engine = create_engine(DATABASE_URL, echo=False)

# START: Database Models (Needed for SQLModel functions)
class Worker(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str

class Alert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Inventory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    item_name: str = Field(unique=True, index=True)
    quantity: int

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
# END: Database Models


# --- AUTHENTICATION CODE ---
load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "your_strong_secret_key_here_a9f8d6e5")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
oauth2_scheme = HTTPBearer()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_worker(
    session: Session = Depends(get_session), 
    token: str = Depends(oauth2_scheme)
) -> Worker:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    worker = session.exec(select(Worker).where(Worker.username == username)).first()
    if worker is None:
        raise credentials_exception
    return worker
# --- END AUTHENTICATION CODE ---


# --- App Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logger.error("FATAL ERROR: GOOGLE_API_KEY environment variable not set.")
else:
    genai.configure(api_key=GOOGLE_API_KEY)

# Import RAG system
try:
    from rag_setup import rag_system
    RAG_INITIALIZED = True
except ImportError:
    logger.error("Could not import rag_system. RAG features will be disabled.")
    RAG_INITIALIZED = False

# --- NEW HELPER FUNCTION: Translate query for RAG ---
async def translate_query_to_english(query: str) -> str:
    """Uses Gemini to translate a query to English for RAG search."""
    try:
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        prompt = f"Translate the following user query to a single sentence of plain English. Return ONLY the translated sentence, with no other commentary: '{query}'"
        
        # --- 2. RUN BLOCKING CALL IN A THREAD ---
        response = await asyncio.to_thread(model.generate_content, prompt)
        
        # Clean up the response, ensuring it's a single line and stripped of whitespace
        return response.text.strip().split('\n')[0]
    except Exception as e:
        logger.error(f"Translation failed, using original query: {e}")
        return query # Fallback to original query
# --- END NEW HELPER FUNCTION ---


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    create_db_and_tables()
    
    # Create default worker account
    with Session(engine) as session:
        existing_worker = session.exec(select(Worker).where(Worker.username == "healthworker")).first()
        if not existing_worker:
            default_worker = Worker(
                username="healthworker",
                hashed_password=get_password_hash("securepass")
            )
            session.add(default_worker)
            session.commit()
            logger.info("Default health worker account created")
        
        # Add sample inventory items
        inventory_items = [
            {"item_name": "Tetanus Vaccine", "quantity": 25},
            {"item_name": "Paracetamol", "quantity": 150},
            {"item_name": "Bandages", "quantity": 200},
            {"item_name": "Antiseptic Solution", "quantity": 50},
            {"item_name": "Thermometers", "quantity": 30}
        ]
        
        for item in inventory_items:
            existing_item = session.exec(select(Inventory).where(Inventory.item_name == item["item_name"])).first()
            if not existing_item:
                session.add(Inventory(**item))
        session.commit()
        logger.info("Sample inventory items added")
    
    # Setup RAG system
    if RAG_INITIALIZED:
        try:
            logger.info("Initializing RAG system...")
            rag_system.setup()
            logger.info("RAG system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {str(e)}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")

# --- FastAPI App Definition ---
app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")

# --- Request/Response Models ---
class ChatRequest(BaseModel):
    query: str
    language: str

class ChatResponse(BaseModel):
    response: str

class AlertResponse(BaseModel):
    id: int
    message: str
    timestamp: datetime

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class BroadcastAlertRequest(BaseModel):
    message: str

class InventoryResponse(BaseModel):
    id: int
    item_name: str
    quantity: int

class UpdateInventoryRequest(BaseModel):
    item_name: str
    quantity: int

class StatusResponse(BaseModel):
    status: str

# --- Helper Function ---
def is_inventory_query(query: str) -> bool:
    inventory_keywords = [
        "inventory", "stock", "available", "supply", "medicine", "vaccine", 
        "tablet", "injection", "bandage", "equipment", "how many", "do you have",
        "इन्वेंटरी", "स्टॉक", "उपलब्ध", "दवा", "टीका",
        "ಇನ್ವೆಂಟರಿ", "ಸ್ಟಾಕ್", "ಲಭ್ಯವಿದೆ", "ಔಷಧ", "ಲಸಿಕೆ"
    ]
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in inventory_keywords)

# --- API Endpoints ---

# Public Endpoints
@api_router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, session: Session = Depends(get_session)):
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Server is not configured with an AI API key.")
        
    try:
        query = request.query
        language = request.language
        context_parts = []
        
        # Determine the query language and translate if necessary
        rag_query = query
        if language != 'en':
            rag_query = await translate_query_to_english(query)
            logger.info(f"Translated query: {rag_query}")
        
        # --- MODIFIED INVENTORY LOGIC ---
        
        # 1. Check for general inventory queries (using the translated query)
        if is_inventory_query(rag_query):
            inventory_items = session.exec(select(Inventory)).all()
            if inventory_items:
                inventory_context = "Current Inventory Status:\n"
                for item in inventory_items:
                    inventory_context += f"- {item.item_name}: {item.quantity} units available\n"
                context_parts.append(inventory_context)
        
        # 2. Check for specific item queries (if not a general query)
        else:
            # Fetch all item names from the database
            all_item_names_query = select(Inventory.item_name)
            all_item_names = [item[0] for item in session.exec(all_item_names_query).all()]
            found_items = []
            
            for item_name in all_item_names:
                # Check if the (lowercase) item name is in the (lowercase) translated query
                if item_name.lower() in rag_query.lower():
                    # If found, get the full item details
                    item_details = session.exec(select(Inventory).where(Inventory.item_name == item_name)).first()
                    if item_details:
                        found_items.append(f"- {item_details.item_name}: {item_details.quantity} units available")
            
            if found_items:
                # If we found specific items, add them to the context
                inventory_context = "Specific Item Availability:\n" + "\n".join(found_items)
                context_parts.append(inventory_context)
        
        # --- END MODIFIED INVENTORY LOGIC ---
        
        if RAG_INITIALIZED:
            # RAG search uses the translated query (rag_query)
            rag_context = rag_system.query(rag_query, k=3)
            if rag_context:
                context_parts.append(f"Knowledge Base Information:\n{rag_context}")
        
        full_context = "\n\n".join(context_parts) if context_parts else "No specific context available."
        
        language_names = {"en": "English", "hi": "Hindi (हिन्दी)", "kn": "Kannada (ಕನ್ನಡ)"}
        language_name = language_names.get(language, "English")
        
        # --- MODIFIED PROMPT: STRICT RAG - NO DISCLAIMERS - USE RELATED CONTEXT ---
        prompt = f"""You are a public health information assistant. Your job is to summarize and translate information from a knowledge base.
Your answer MUST be in {language_name}.

**CRITICAL INSTRUCTIONS:**
1.  Your task is to answer the user's `QUERY` using **ONLY** the provided `CONTEXT`.
2.  **DO NOT** add any of your own knowledge, opinions, or medical disclaimers (e.g., "I am an AI", "consult a doctor").
3.  If the `CONTEXT` contains information that is *related* to the `QUERY` (e.g., CONTEXT has "severe headache" and QUERY is "headache"), you **MUST** summarize that related information. Do not apologize.
4.  If the `CONTEXT` is completely empty or has zero relevance, and only in that case, politely state in {language_name} that you do not have that specific information.

CONTEXT:
{full_context}

QUERY: {query}

Answer in {language_name}:"""
        
        # --- MODEL NAME (Using the model confirmed to work) ---
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        # --- 3. RUN BLOCKING CALL IN A THREAD ---
        response = await asyncio.to_thread(model.generate_content, prompt)
        
        return ChatResponse(response=response.text)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@api_router.get("/get-alerts", response_model=List[AlertResponse])
async def get_alerts(session: Session = Depends(get_session)):
    alerts = session.exec(select(Alert).order_by(Alert.timestamp.desc())).all()
    return alerts

# Worker Endpoints
@api_router.post("/worker/login", response_model=LoginResponse)
async def worker_login(request: LoginRequest, session: Session = Depends(get_session)):
    worker = session.exec(select(Worker).where(Worker.username == request.username)).first()
    
    if not worker or not verify_password(request.password, worker.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token = create_access_token(data={"sub": worker.username})
    return LoginResponse(access_token=access_token)

@api_router.post("/worker/broadcast-alert", response_model=StatusResponse)
async def broadcast_alert(
    request: BroadcastAlertRequest,
    session: Session = Depends(get_session),
    current_worker: Worker = Depends(get_current_worker) # <-- Protected
):
    new_alert = Alert(message=request.message)
    session.add(new_alert)
    session.commit()
    return StatusResponse(status="success")

@api_router.get("/worker/get-inventory", response_model=List[InventoryResponse])
async def get_inventory(
    session: Session = Depends(get_session),
    current_worker: Worker = Depends(get_current_worker) # <-- Protected
):
    inventory = session.exec(select(Inventory)).all()
    return inventory

@api_router.post("/worker/update-inventory", response_model=StatusResponse)
async def update_inventory(
    request: UpdateInventoryRequest,
    session: Session = Depends(get_session),
    current_worker: Worker = Depends(get_current_worker) # <-- Protected
):
    item = session.exec(select(Inventory).where(Inventory.item_name == request.item_name)).first()
    
    if item:
        item.quantity = request.quantity
    else:
        new_item = Inventory(item_name=request.item_name, quantity=request.quantity)
        session.add(new_item)
    
    session.commit()
    return StatusResponse(status="success")

# --- NEW ENDPOINT (Clear Alerts) ---
@api_router.post("/worker/clear-alerts", response_model=StatusResponse)
async def clear_alerts(
    session: Session = Depends(get_session),
    current_worker: Worker = Depends(get_current_worker) # <-- Protected
):
    try:
        statement = delete(Alert)
        session.exec(statement)
        session.commit()
        return StatusResponse(status="success")
    except Exception as e:
        logger.error(f"Error clearing alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear alerts")
# --- END NEW ENDPOINT ---

# --- Final App Setup ---

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- To run this file, use: ---
# uvicorn auth:app --reload

