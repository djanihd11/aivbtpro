import os
import asyncio
import logging
from pathlib import Path
import markdown
from bs4 import BeautifulSoup
import re

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

import google.generativeai as genai
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer # For local embeddings if preferred

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# System prompt for the agent
DEFAULT_SYSTEM_PROMPT = """You are an expert in vectorbt and vectorbtpro, a Python library for backtesting and analyzing trading strategies.
Your goal is to provide accurate, helpful, and code-centric answers to users' questions about vectorbt and vectorbtpro.
When a user asks a question, you will be given relevant context from the vectorbtpro documentation.
Use this context to inform your answer. If the context is insufficient or the question is ambiguous, ask clarifying questions.
If the user's query can be best answered with a code example, provide a complete, runnable Python code snippet using vectorbtpro.
Ensure the code is well-commented and directly addresses the user's query.
If the query is about a concept, explain it clearly and concisely, referencing the documentation where appropriate.
Do not make up information. If you don't know the answer, say so.
You can also be asked to explain code, debug code, or convert code from other libraries to vectorbtpro.
When providing code, always ensure it is for vectorbtpro.
You are interacting with a user through a JupyterLab extension. The user can execute the code you provide.
Focus on being helpful and providing practical, actionable solutions.
If you are providing a Python code block, make sure it is enclosed in triple backticks with the language specifier, like this:
```python
# Your Python code here
```
"""

class VectorBTProExpert:
    def __init__(self, gemini_api_key: str, docs_path: str):
        self.gemini_api_key = gemini_api_key
        self.docs_path = Path(docs_path)
        
        genai.configure(api_key=self.gemini_api_key)
        self.model_name = 'gemini-pro' # Using gemini-pro for broader compatibility
        self.gen_model = genai.GenerativeModel(self.model_name)
        
        self.db_path = Path("/home/jovyan/work/knowledge_base")
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(path=str(self.db_path))
        
        # Using a local sentence transformer model for embeddings
        self.embedding_model_name = 'all-MiniLM-L6-v2'
        self.sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.embedding_model_name
        )
        
        self.collection_name = "vectorbtpro_docs"
        self.collection = None # Will be initialized in initialize_knowledge_base
        
        self.system_prompt = DEFAULT_SYSTEM_PROMPT
        self.is_initialized = False
        logger.info("VectorBTProExpert initialized.")

    def _split_text(self, text: str, max_chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Splits text into overlapping chunks."""
        if not text:
            return []
        words = text.split()
        if not words:
            return []
            
        chunks = []
        current_chunk = []
        current_length = 0
        for word in words:
            if current_length + len(word) + 1 <= max_chunk_size:
                current_chunk.append(word)
                current_length += len(word) + 1
            else:
                chunks.append(" ".join(current_chunk))
                # Start new chunk with overlap
                overlap_start_index = max(0, len(current_chunk) - overlap // len(" ".join(words[:overlap//5])) if words else 0) # Approximate word overlap
                current_chunk = current_chunk[overlap_start_index:] + [word]
                current_length = len(" ".join(current_chunk))
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        return chunks

    async def initialize_knowledge_base(self):
        logger.info("Initializing knowledge base...")
        try:
            self.collection = await asyncio.to_thread(
                self.chroma_client.get_or_create_collection,
                name=self.collection_name,
                embedding_function=self.sentence_transformer_ef
            )
            logger.info(f"ChromaDB collection '{self.collection_name}' retrieved/created.")
        except Exception as e:
            logger.error(f"Error initializing ChromaDB collection: {e}")
            self.is_initialized = False
            return

        if not self.docs_path.exists() or not self.docs_path.is_dir():
            logger.error(f"Documentation path not found: {self.docs_path}")
            self.is_initialized = False # Should not proceed if docs are missing
            return

        markdown_files = list(self.docs_path.rglob("*.md"))
        if not markdown_files:
            logger.warning(f"No markdown files found in {self.docs_path}. Knowledge base will be empty.")
            self.is_initialized = True # Initialized, but empty
            return

        logger.info(f"Found {len(markdown_files)} markdown files to process.")
        
        documents_to_add = []
        metadatas_to_add = []
        ids_to_add = []
        
        # Check existing documents to avoid duplicates efficiently
        existing_ids = set()
        if self.collection.count() > 0: # Only query if collection is not empty
            logger.info("Checking existing documents in ChromaDB to prevent duplicates...")
            # Fetch all IDs if the collection is not excessively large, or implement paginated fetching.
            # For simplicity, fetching all. This might be slow for very large collections.
            try:
                results = await asyncio.to_thread(self.collection.get, include=[]) # only get ids
                existing_ids.update(results['ids'])
                logger.info(f"Found {len(existing_ids)} existing document IDs in the collection.")
            except Exception as e:
                 logger.error(f"Error fetching existing document IDs from ChromaDB: {e}. Proceeding without duplicate check for new items.")


        for md_file in markdown_files:
            try:
                # Read file asynchronously
                async with asyncio.TaskGroup() as tg: # Python 3.11+
                     md_content_task = tg.create_task(asyncio.to_thread(md_file.read_text, encoding='utf-8'))
                md_content = md_content_task.result()
                
                # Convert markdown to plain text (can be synchronous as it's CPU bound)
                html = markdown.markdown(md_content)
                soup = BeautifulSoup(html, 'html.parser')
                plain_text = soup.get_text(separator='\n', strip=True)
                
                chunks = self._split_text(plain_text)
                
                file_chunk_count = 0
                for i, chunk in enumerate(chunks):
                    doc_id = f"{md_file.stem}_{i}"
                    if doc_id in existing_ids:
                        # logger.info(f"Document {doc_id} already in collection. Skipping.") # Too verbose
                        continue

                    documents_to_add.append(chunk)
                    metadatas_to_add.append({"source": str(md_file.relative_to(self.docs_path))})
                    ids_to_add.append(doc_id)
                    file_chunk_count +=1
                
                if file_chunk_count > 0:
                    logger.info(f"Processed {md_file.name}, prepared {file_chunk_count} new chunks.")

            except Exception as e:
                logger.error(f"Error processing file {md_file}: {e}")

        if documents_to_add:
            try:
                # Batch add to ChromaDB
                await asyncio.to_thread(
                    self.collection.add,
                    documents=documents_to_add,
                    metadatas=metadatas_to_add,
                    ids=ids_to_add
                )
                logger.info(f"Successfully added {len(documents_to_add)} new document chunks to ChromaDB.")
            except Exception as e:
                logger.error(f"Error adding documents to ChromaDB: {e}")
        
        self.is_initialized = True
        logger.info("Knowledge base initialization complete.")

    async def search_knowledge_base(self, query: str, n_results: int = 5) -> List[str]:
        if not self.is_initialized or not self.collection:
            logger.warning("Knowledge base not initialized. Search cannot be performed.")
            return []
        try:
            results = await asyncio.to_thread(
                self.collection.query,
                query_texts=[query],
                n_results=n_results,
                include=["documents"] # Only request documents
            )
            return results['documents'][0] if results and results['documents'] else []
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []

    async def generate_response(self, user_query: str, context: Optional[List[Dict[str, str]]] = None) -> str:
        if not self.is_initialized:
            return "Error: Agent not initialized. Please initialize first."
        
        logger.info(f"Generating response for query: {user_query}")
        
        # 1. Search knowledge base
        rag_context_chunks = await self.search_knowledge_base(user_query)
        rag_context_str = "\n\n".join(rag_context_chunks)
        
        # 2. Construct prompt
        prompt_parts = [self.system_prompt]
        
        if rag_context_str:
            prompt_parts.append("\nRelevant context from documentation:\n")
            prompt_parts.append(rag_context_str)
            
        if context: # Previous conversation history
            prompt_parts.append("\nPrevious conversation history:\n")
            for turn in context: # Ensure context is a list of dicts
                if isinstance(turn, dict) and "role" in turn and "content" in turn:
                    prompt_parts.append(f"{turn['role']}: {turn['content']}")
                else:
                    logger.warning(f"Skipping malformed context entry: {turn}")

        prompt_parts.append(f"\nUser query: {user_query}")
        prompt_parts.append("\nAnswer:\n") # Add a clear marker for the LLM to start its answer
        
        final_prompt = "\n".join(prompt_parts)
        
        # logger.debug(f"Final prompt for Gemini: {final_prompt}") # Be careful with logging full prompts

        try:
            # Gemini SDK's generate_content is synchronous, run in thread
            response = await asyncio.to_thread(
                self.gen_model.generate_content,
                final_prompt,
                # Safety settings can be configured here if needed
                # generation_config=genai.types.GenerationConfig(...)
            )
            if response and response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                 model_response_text = "".join(part.text for part in response.candidates[0].content.parts)
            else:
                # Check for blocked responses (safety settings, etc.)
                if response and response.prompt_feedback and response.prompt_feedback.block_reason:
                    block_reason = response.prompt_feedback.block_reason
                    logger.warning(f"Response blocked by API. Reason: {block_reason}")
                    model_response_text = f"Sorry, I could not generate a response. The request was blocked due to: {block_reason}."
                else:
                    model_response_text = "Sorry, I could not generate a response at this time (empty or unexpected response structure)."
                    logger.warning(f"Unexpected response structure from Gemini API: {response}")

        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return "Error: Could not connect to the generative model."
            
        return model_response_text

    def execute_code(self, code: str) -> Dict[str, Any]:
        """
        Placeholder for code execution.
        In this setup, code execution is primarily handled by the Jupyter extension.
        This method can be used for validation or other purposes if needed.
        """
        logger.info(f"Placeholder: Code execution requested for: \n{code}")
        return {"status": "success", "output": "Code execution placeholder - not actually run on backend."}


# FastAPI App
app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent: Optional[VectorBTProExpert] = None

# Pydantic Models
class InitRequest(BaseModel):
    gemini_api_key: str
    docs_path: str = "/home/jovyan/vectorbtpro/docs" # Default path inside the Docker container

class QueryRequest(BaseModel):
    query: str
    context: Optional[List[Dict[str, str]]] = None # e.g. [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

class QueryResponse(BaseModel):
    response: str
    code: Optional[str] = None
    status: str # e.g., "success", "error", "agent_not_initialized"

def extract_python_code(text: str) -> Optional[str]:
    """Extracts Python code from a markdown-style code block."""
    match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

# API Endpoints
@app.post("/initialize")
async def initialize_agent_endpoint(request: InitRequest): # Renamed to avoid conflict with global 'initialize_agent'
    global agent
    if not request.gemini_api_key:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY is required.")
    try:
        agent = VectorBTProExpert(gemini_api_key=request.gemini_api_key, docs_path=request.docs_path)
        await agent.initialize_knowledge_base() # This is an async function
        
        if agent.is_initialized:
            # Check knowledge base status more accurately
            kb_count = 0
            if agent.collection:
                 kb_count = await asyncio.to_thread(agent.collection.count)
            
            if kb_count > 0:
                return {"status": "success", "message": f"Agent initialized successfully. Knowledge base loaded with {kb_count} documents."}
            elif agent.docs_path.exists() and not list(agent.docs_path.rglob("*.md")):
                 msg = f"Agent initialized, but knowledge base is empty: No markdown files found in '{agent.docs_path}'."
                 logger.warning(msg)
                 return {"status": "warning", "message": msg}
            elif not agent.docs_path.exists():
                 msg = f"Agent initialized, but knowledge base could not be built: Documentation path '{agent.docs_path}' not found."
                 logger.warning(msg)
                 return {"status": "warning", "message": msg}
            else:
                 msg = "Agent initialized, but knowledge base is empty or incomplete. Check logs."
                 logger.warning(msg)
                 return {"status": "warning", "message": msg}

        else: # agent.is_initialized is False
            # This case implies a more fundamental failure during VectorBTProExpert.__init__ or early in initialize_knowledge_base
            msg = "Agent initialization failed. Check logs for errors (e.g., ChromaDB setup, API key issues for embedding model if not local)."
            logger.error(msg) # Log as error if is_initialized is False
            raise HTTPException(status_code=500, detail=msg)


    except Exception as e:
        logger.error(f"Error initializing agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initialize agent: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query_agent_endpoint(request: QueryRequest): # Renamed
    global agent
    if not agent or not agent.is_initialized:
        return QueryResponse(response="Agent not initialized. Please call /initialize first.", code=None, status="agent_not_initialized")
    
    try:
        raw_response = await agent.generate_response(request.query, request.context)
        extracted_code = extract_python_code(raw_response)
        return QueryResponse(response=raw_response, code=extracted_code, status="success")
    except Exception as e:
        logger.error(f"Error during query processing: {e}", exc_info=True)
        return QueryResponse(response=f"An error occurred: {str(e)}", code=None, status="error")

@app.get("/status")
async def get_status():
    global agent
    if agent and agent.is_initialized:
        kb_status = "not loaded or empty"
        count = 0
        if agent.collection:
            try:
                count = await asyncio.to_thread(agent.collection.count)
                if count > 0:
                    kb_status = f"loaded with {count} documents"
                else:
                    kb_status = "loaded but empty"
            except Exception as e:
                logger.error(f"Could not get KB count: {e}")
                kb_status = "loaded, but count unavailable"
        
        return {
            "agent_status": "initialized",
            "model_name": agent.model_name,
            "docs_path": str(agent.docs_path),
            "knowledge_base_status": kb_status,
            "collection_name": agent.collection_name,
            "db_path": str(agent.db_path)
        }
    return {"agent_status": "not_initialized"}

@app.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    global agent # Ensure agent is accessible
    if not agent or not agent.is_initialized:
        await websocket.send_json({"response": "Agent not initialized. Please ensure it's initialized via POST /initialize.", "code": None, "status": "error"})
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_json()
            query = data.get("query")
            context = data.get("context") # Optional conversation history

            if not query:
                await websocket.send_json({"response": "Query cannot be empty.", "code": None, "status": "error_validation"})
                continue

            raw_response = await agent.generate_response(query, context)
            extracted_code = extract_python_code(raw_response)
            await websocket.send_json({"response": raw_response, "code": extracted_code, "status": "success"})
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket {websocket.client} disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            # Send error details before closing if possible
            await websocket.send_json({"response": f"An error occurred: {str(e)}", "code": None, "status": "error_server"})
        except Exception: # If sending fails too
            pass # Logged already, can't inform client
        # Consider specific close codes: https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent/code
        await websocket.close(code=1011) # Internal Error

async def _auto_initialize_agent_impl(): # Renamed to avoid conflict
    """Optionally initializes the agent on startup if API key is available."""
    global agent
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    # Default to /home/jovyan/vectorbtpro/docs if not set, which is where Dockerfile copies it
    docs_path = os.getenv("DOCS_PATH", "/home/jovyan/vectorbtpro/docs") 

    if gemini_api_key:
        logger.info(f"GEMINI_API_KEY found in environment. Attempting to auto-initialize agent with docs from: {docs_path}")
        try:
            agent = VectorBTProExpert(gemini_api_key=gemini_api_key, docs_path=docs_path)
            await agent.initialize_knowledge_base() # This is an async function
            if agent.is_initialized:
                kb_count = 0
                if agent.collection:
                    kb_count = await asyncio.to_thread(agent.collection.count)
                logger.info(f"Agent auto-initialized successfully. Knowledge base has {kb_count} documents.")
            else:
                logger.warning("Agent auto-initialization completed, but knowledge base might have issues or is_initialized is False. Check logs.")
        except Exception as e:
            logger.error(f"Auto-initialization failed: {e}", exc_info=True)
    else:
        logger.info("GEMINI_API_KEY not found in environment. Skipping auto-initialization. Agent must be initialized via API call to /initialize.")

@app.on_event("startup")
async def startup_event():
    # This allows auto-initialization to run in the background without blocking startup
    # if the GEMINI_API_KEY is set in the environment.
    logger.info("FastAPI application startup...")
    if os.getenv("AUTO_INITIALIZE_AGENT", "true").lower() == "true": # Allow disabling auto-init
        asyncio.create_task(_auto_initialize_agent_impl())
    else:
        logger.info("AUTO_INITIALIZE_AGENT is not 'true'. Skipping auto-initialization.")


if __name__ == "__main__":
    import uvicorn
    # Default port to 8000, can be overridden by PORT env var (common in containers)
    port = int(os.getenv("PORT", 8000))
    # Default host to 0.0.0.0 to be accessible externally, can be overridden
    host = os.getenv("HOST", "0.0.0.0")
    
    # Uvicorn logging level can be controlled via environment or config.
    # The "reload" option is mainly for development. For production, it's usually False.
    # reload_val = os.getenv("UVICORN_RELOAD", "False").lower() == "true"
    
    logger.info(f"Starting Uvicorn server on {host}:{port}")
    
    # Note: The auto_initialize_agent via startup event is preferred over blocking here.
    # If you need to ensure initialization before serving, you might await it here,
    # but that would make the server startup block.
    
    uvicorn.run(app, host=host, port=port, log_level="info") #reload=reload_val
```
