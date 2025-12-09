import os
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
import logging

logger = logging.getLogger(__name__)

# --- MODIFIED SECTION START ---
# Go up one level from the current file (backend/) to the project root (Aacharya AI/)
ROOT_DIR = Path(__file__).parent.parent 
KNOWLEDGE_BASE_DIR = ROOT_DIR / "knowledge_base" # This now correctly points to Aacharya AI/knowledge_base

# CHROMA_DB_DIR should stay relative to this file (inside the backend folder)
CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"
# --- MODIFIED SECTION END ---


class RAGSystem:
    def __init__(self):
        self.vectorstore = None
        self.embeddings = None
        
    def setup(self):
        """Initialize the RAG system with knowledge base documents"""
        try:
            logger.info("Setting up RAG system...")
            
            # Initialize multilingual embeddings
            logger.info("Loading multilingual embeddings model...")
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                model_kwargs={'device': 'cpu'}
            )
            
            # Check if Chroma DB already exists
            if CHROMA_DB_DIR.exists() and any(CHROMA_DB_DIR.iterdir()):
                logger.info("Loading existing Chroma DB...")
                self.vectorstore = Chroma(
                    persist_directory=str(CHROMA_DB_DIR),
                    embedding_function=self.embeddings
                )
                logger.info("RAG system loaded from existing database")
                return
            
            # Load documents from knowledge base
            logger.info(f"Loading documents from {KNOWLEDGE_BASE_DIR}...")
            
            # Load text files
            txt_loader = DirectoryLoader(
                str(KNOWLEDGE_BASE_DIR),
                glob="**/*.txt",
                loader_cls=TextLoader,
                loader_kwargs={'autodetect_encoding': True}
            )
            txt_docs = txt_loader.load()
            logger.info(f"Loaded {len(txt_docs)} text documents")
            
            # Load PDF files
            pdf_loader = DirectoryLoader(
                str(KNOWLEDGE_BASE_DIR),
                glob="**/*.pdf",
                loader_cls=PyPDFLoader
            )
            pdf_docs = pdf_loader.load()
            logger.info(f"Loaded {len(pdf_docs)} PDF documents")
            
            # Combine all documents
            all_docs = txt_docs + pdf_docs
            
            if not all_docs:
                logger.warning(f"No documents found in {KNOWLEDGE_BASE_DIR}! Make sure the path is correct.")
                return
            
            # Split documents into chunks
            logger.info("Splitting documents into chunks...")
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            chunks = text_splitter.split_documents(all_docs)
            logger.info(f"Created {len(chunks)} text chunks")
            
            # Create vector store
            logger.info("Creating Chroma vector store...")
            self.vectorstore = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=str(CHROMA_DB_DIR)
            )
            
            logger.info("RAG system setup complete!")
            
        except Exception as e:
            logger.error(f"Error setting up RAG system: {str(e)}")
            raise
    
    def query(self, query_text: str, k: int = 3) -> str:
        """Query the RAG system and return relevant context"""
        # --- DEFENSIVE CHECK MODIFIED FOR RELOAD ---
        if not self.vectorstore:
             # Try loading the database if it exists but wasn't fully initialized during setup
            if CHROMA_DB_DIR.exists() and any(CHROMA_DB_DIR.iterdir()):
                logger.info("Vectorstore was None, attempting to reload Chroma DB for query...")
                try:
                    self.vectorstore = Chroma(
                        persist_directory=str(CHROMA_DB_DIR),
                        embedding_function=self.embeddings
                    )
                except Exception as load_error:
                    logger.error(f"Failed to load vectorstore on query attempt: {str(load_error)}")
                    return ""
            else:
                logger.warning("Query attempted but vectorstore is not available and database is empty.")
                return ""
        # --- END DEFENSIVE CHECK ---
        
        try:
            # The multilingual model handles the cross-lingual search automatically
            docs = self.vectorstore.similarity_search(query_text, k=k)
            context = "\n\n".join([doc.page_content for doc in docs])
            return context
        except Exception as e:
            logger.error(f"Error querying RAG system: {str(e)}")
            return ""

# Global RAG instance
rag_system = RAGSystem()
