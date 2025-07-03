import os
import logging
import json
import faiss
import numpy as np
from typing import List, Dict, Any
from openai import OpenAI

class RAGChain:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = "text-embedding-ada-002"
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.chat_model = "gpt-4o"
        self.top_k = 3
        
        # Small talk responses
        self.small_talk_responses = {
            "hi": "Hi there! How can I assist you?",
            "hello": "Hello! What can I help you with today?",
            "how are you": "I'm great, thank you! What can I help you with?",
            "hey": "Hey! How can I help you today?",
            "good morning": "Good morning! How can I assist you?",
            "good afternoon": "Good afternoon! What can I help you with?",
            "good evening": "Good evening! How can I help you today?",
            "thanks": "You're welcome! Is there anything else I can help you with?",
            "thank you": "You're welcome! Is there anything else I can help you with?",
            "bye": "Goodbye! Feel free to ask if you need any help.",
            "goodbye": "Goodbye! Have a great day!"
        }
    
    def is_small_talk(self, question: str) -> bool:
        """Check if the question is small talk"""
        question_lower = question.lower().strip()
        return question_lower in self.small_talk_responses
    
    def get_small_talk_response(self, question: str) -> str:
        """Get response for small talk"""
        question_lower = question.lower().strip()
        return self.small_talk_responses.get(question_lower, "")
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text"""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=[text]
            )
            return response.data[0].embedding
        except Exception as e:
            logging.error(f"Error getting embedding: {str(e)}")
            raise
    
    def load_index_and_metadata(self, index_folder: str) -> tuple:
        """Load FAISS index and metadata"""
        index_path = os.path.join(index_folder, 'index.faiss')
        metadata_path = os.path.join(index_folder, 'metadata.json')
        
        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            return None, None
        
        try:
            index = faiss.read_index(index_path)
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            return index, metadata
        except Exception as e:
            logging.error(f"Error loading index and metadata: {str(e)}")
            return None, None
    
    def retrieve_relevant_chunks(self, question: str, index_folder: str) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks for a question"""
        index, metadata = self.load_index_and_metadata(index_folder)
        
        if index is None or metadata is None:
            return []
        
        try:
            # Get question embedding
            question_embedding = self.get_embedding(question)
            question_array = np.array([question_embedding], dtype='float32')
            
            # Search in FAISS index
            distances, indices = index.search(question_array, self.top_k)
            
            # Get relevant chunks
            relevant_chunks = []
            for i, idx in enumerate(indices[0]):
                if idx < len(metadata['chunks']):
                    chunk = metadata['chunks'][idx].copy()
                    chunk['similarity_score'] = float(distances[0][i])
                    relevant_chunks.append(chunk)
            
            return relevant_chunks
            
        except Exception as e:
            logging.error(f"Error retrieving relevant chunks: {str(e)}")
            return []
    
    def generate_answer(self, question: str, relevant_chunks: List[Dict[str, Any]]) -> str:
        """Generate answer using OpenAI chat model"""
        if not relevant_chunks:
            return "I couldn't find any relevant information. Please try a different question."
        
        # Create context from relevant chunks
        context = "\n\n".join([
            f"From {chunk['source']}:\n{chunk['text']}"
            for chunk in relevant_chunks
        ])
        
        # Create prompt
        system_prompt = """You are a helpful assistant that answers questions based on the provided context. 
        Follow these guidelines:
        1. Provide short, clear, and direct answers
        2. Use only the information from the provided context
        3. If the context doesn't contain enough information to answer the question, politely say so
        4. Do not make up or hallucinate information
        5. Be concise and avoid lengthy explanations unless specifically asked
        """
        
        user_prompt = f"""Context:
        {context}
        
        Question: {question}
        
        Please provide a clear and concise answer based on the context above."""
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"Error generating answer: {str(e)}")
            return "I'm sorry, I encountered an error while processing your question. Please try again."
    
    def get_answer(self, question: str, index_folder: str) -> str:
        """Get answer for a question"""
        # Check for small talk
        if self.is_small_talk(question):
            return self.get_small_talk_response(question)
        
        # Retrieve relevant chunks
        relevant_chunks = self.retrieve_relevant_chunks(question, index_folder)
        
        # Generate answer
        answer = self.generate_answer(question, relevant_chunks)
        
        return answer
