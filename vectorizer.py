import os
import logging
from typing import List
import json
from docx import Document
import PyPDF2
import faiss
import numpy as np
from openai import OpenAI
import tiktoken

class DocumentVectorizer:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            api_key = api_key.strip()  # Remove any whitespace
        self.openai_client = OpenAI(api_key=api_key)
        self.embedding_model = "text-embedding-ada-002"
        self.chunk_size = 500
        self.chunk_overlap = 50
        self.encoding = tiktoken.encoding_for_model("gpt-4o")
        
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            logging.error(f"Error extracting text from PDF {file_path}: {str(e)}")
            raise
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logging.error(f"Error extracting text from DOCX {file_path}: {str(e)}")
            raise
    
    def chunk_text(self, text: str, filename: str) -> List[dict]:
        """Split text into chunks with overlap"""
        chunks = []
        
        # Split by sentences first
        sentences = text.split('.')
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_tokens = len(self.encoding.encode(sentence))
            
            # If adding this sentence would exceed chunk size, save current chunk
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                chunks.append({
                    'text': current_chunk.strip(),
                    'source': filename,
                    'chunk_id': len(chunks)
                })
                
                # Start new chunk with overlap
                overlap_text = current_chunk.split()[-self.chunk_overlap:]
                current_chunk = " ".join(overlap_text) + " " + sentence
                current_tokens = len(self.encoding.encode(current_chunk))
            else:
                current_chunk += " " + sentence
                current_tokens += sentence_tokens
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append({
                'text': current_chunk.strip(),
                'source': filename,
                'chunk_id': len(chunks)
            })
        
        return chunks
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of texts"""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            return [embedding.embedding for embedding in response.data]
        except Exception as e:
            logging.error(f"Error getting embeddings: {str(e)}")
            raise
    
    def process_documents(self, file_paths: List[str], index_folder: str):
        """Process documents and create FAISS index"""
        logging.info(f"Processing {len(file_paths)} documents")
        
        all_chunks = []
        
        # Extract text and create chunks from all documents
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            logging.info(f"Processing file: {filename}")
            
            try:
                # Extract text based on file type
                if file_path.lower().endswith('.pdf'):
                    text = self.extract_text_from_pdf(file_path)
                elif file_path.lower().endswith('.docx'):
                    text = self.extract_text_from_docx(file_path)
                else:
                    logging.warning(f"Unsupported file type: {filename}")
                    continue
                
                if not text.strip():
                    logging.warning(f"No text extracted from {filename}")
                    continue
                
                # Create chunks
                chunks = self.chunk_text(text, filename)
                all_chunks.extend(chunks)
                logging.info(f"Created {len(chunks)} chunks from {filename}")
                
            except Exception as e:
                logging.error(f"Error processing {filename}: {str(e)}")
                continue
        
        if not all_chunks:
            raise ValueError("No text chunks were created from the uploaded documents")
        
        # Get embeddings for all chunks
        logging.info(f"Getting embeddings for {len(all_chunks)} chunks")
        chunk_texts = [chunk['text'] for chunk in all_chunks]
        
        # Process embeddings in batches to avoid API limits
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(chunk_texts), batch_size):
            batch = chunk_texts[i:i + batch_size]
            embeddings = self.get_embeddings(batch)
            all_embeddings.extend(embeddings)
        
        # Create FAISS index
        logging.info("Creating FAISS index")
        embedding_dim = len(all_embeddings[0])
        index = faiss.IndexFlatL2(embedding_dim)
        
        # Add embeddings to index
        embeddings_array = np.array(all_embeddings, dtype='float32')
        index.add(embeddings_array)
        
        # Save index and metadata
        index_path = os.path.join(index_folder, 'index.faiss')
        metadata_path = os.path.join(index_folder, 'metadata.json')
        
        faiss.write_index(index, index_path)
        
        # Save metadata
        metadata = {
            'chunks': all_chunks,
            'total_chunks': len(all_chunks),
            'embedding_model': self.embedding_model,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap
        }
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logging.info(f"FAISS index created successfully with {len(all_chunks)} chunks")
