import os
import logging
import json
import faiss
import numpy as np
import random
from typing import List, Dict, Any
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from session_memory import session_manager

class RAGChain:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            api_key = api_key.strip()  # Remove any whitespace
        self.openai_client = OpenAI(api_key=api_key)
        self.embedding_model = "text-embedding-ada-002"
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.chat_model = "gpt-4o"
        self.top_k = 3
        
        # Initialize LangChain components
        self.langchain_llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            api_key=api_key
        )
        
        # Create conversation prompt template
        self.conversation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant with access to a knowledge base. 
            Use the provided context and conversation history to answer questions accurately.
            If you don't know something, say so clearly.
            
            Context from knowledge base:
            {context}
            
            Previous conversation:
            {conversation_history}"""),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        # Small talk responses with multiple variations
        self.small_talk_responses = {
            "hi": [
                "Hi there! How can I assist you?",
                "Hello! What brings you here today?",
                "Hey! How can I help you?",
                "Hi! What can I do for you today?",
                "Hello there! Ready to chat?"
            ],
            "hello": [
                "Hello! What can I help you with today?",
                "Hi there! How can I assist you?",
                "Hello! What would you like to know?",
                "Hey! How can I help?",
                "Hello! What's on your mind today?"
            ],
            "how are you": [
                "I'm great, thank you! What can I help you with?",
                "I'm doing well! How can I assist you today?",
                "I'm fantastic! What brings you here?",
                "I'm doing great! What can I help you with?",
                "I'm wonderful! How can I help you today?"
            ],
            "hey": [
                "Hey! How can I help you today?",
                "Hi there! What can I do for you?",
                "Hey! What's up?",
                "Hello! How can I assist you?",
                "Hey there! What can I help you with?"
            ],
            "good morning": [
                "Good morning! How can I assist you?",
                "Good morning! What can I help you with today?",
                "Morning! How can I help you?",
                "Good morning! Ready to get started?",
                "Good morning! What's on your agenda today?"
            ],
            "good afternoon": [
                "Good afternoon! What can I help you with?",
                "Good afternoon! How can I assist you?",
                "Afternoon! What can I do for you?",
                "Good afternoon! How are things going?",
                "Good afternoon! What brings you here?"
            ],
            "good evening": [
                "Good evening! How can I help you today?",
                "Good evening! What can I assist you with?",
                "Evening! How can I help?",
                "Good evening! What's on your mind?",
                "Good evening! How can I be of service?"
            ],
            "thanks": [
                "You're welcome! Is there anything else I can help you with?",
                "Happy to help! Anything else you need?",
                "No problem! What else can I do for you?",
                "You're very welcome! Any other questions?",
                "Glad I could help! Is there more I can assist with?"
            ],
            "thank you": [
                "You're welcome! Is there anything else I can help you with?",
                "My pleasure! What else can I do for you?",
                "Happy to help! Any other questions?",
                "You're very welcome! How else can I assist?",
                "Glad I could help! Anything else you need?"
            ],
            "bye": [
                "Goodbye! Feel free to ask if you need any help.",
                "See you later! Come back anytime!",
                "Take care! Happy to help again anytime.",
                "Bye! Don't hesitate to return if you need assistance.",
                "Farewell! Hope to chat again soon!"
            ],
            "goodbye": [
                "Goodbye! Have a great day!",
                "See you later! Take care!",
                "Farewell! Hope you have a wonderful day!",
                "Goodbye! It was great chatting with you!",
                "Take care! Come back anytime!"
            ]
        }
    
    def is_small_talk(self, question: str) -> bool:
        """Check if the question is small talk"""
        question_lower = question.lower().strip()
        return question_lower in self.small_talk_responses
    
    def get_small_talk_response(self, question: str) -> str:
        """Get response for small talk"""
        question_lower = question.lower().strip()
        responses = self.small_talk_responses.get(question_lower, [])
        if responses:
            return random.choice(responses)
        return ""
    
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
    
    def generate_answer_with_memory(self, question: str, relevant_chunks: List[Dict[str, Any]], session_id: str = None) -> str:
        """Generate answer using LangChain with session memory"""
        if not relevant_chunks:
            return "I couldn't find any relevant information. Please try a different question."
        
        # Create context from relevant chunks
        context = "\n\n".join([
            f"From {chunk['source']}:\n{chunk['text']}"
            for chunk in relevant_chunks
        ])
        
        # Get conversation history if session_id provided
        conversation_history = ""
        if session_id:
            conversation_history = session_manager.get_memory_context(session_id)
        
        try:
            # Create messages for LangChain
            messages = [
                SystemMessage(content=f"""You are a helpful AI assistant with access to a knowledge base. 
                Use the provided context and conversation history to answer questions accurately.
                If you don't know something, say so clearly.
                
                Context from knowledge base:
                {context}
                
                Previous conversation:
                {conversation_history}"""),
                HumanMessage(content=question)
            ]
            
            # Generate response using LangChain
            response = self.langchain_llm.invoke(messages)
            answer = response.content.strip()
            
            # Add to session memory if session_id provided
            if session_id:
                session_manager.add_user_message(session_id, question)
                session_manager.add_ai_message(session_id, answer)
            
            return answer
            
        except Exception as e:
            logging.error(f"Error generating answer with memory: {str(e)}")
            return "I'm sorry, I encountered an error while processing your question. Please try again."
    
    def get_answer(self, question: str, index_folder: str, session_id: str = None) -> str:
        """Get answer for a question with optional session memory"""
        # Check for small talk
        if self.is_small_talk(question):
            response = self.get_small_talk_response(question)
            # Add to session memory if session_id provided
            if session_id:
                session_manager.add_user_message(session_id, question)
                session_manager.add_ai_message(session_id, response)
            return response
        
        # Retrieve relevant chunks
        relevant_chunks = self.retrieve_relevant_chunks(question, index_folder)
        
        # Generate answer with memory
        answer = self.generate_answer_with_memory(question, relevant_chunks, session_id)
        
        return answer
