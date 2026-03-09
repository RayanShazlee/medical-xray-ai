from typing import Dict, List, Any, Optional
import pinecone
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
import json
from PyPDF2 import PdfReader
import numpy as np
from pathlib import Path
from utils.pdf_processor import PDFProcessor
import base64

load_dotenv()

class BookVectorDB:
    def __init__(self, index_name: str = "book-knowledge", namespace: str = "books"):
        """Initialize the book vector database."""
        self.pc = pinecone.Pinecone(
            api_key=os.getenv("PINECONE_API_KEY")
        )
        
        # Create index for book content if it doesn't exist
        try:
            existing_indexes = self.pc.list_indexes().names()
            if index_name not in existing_indexes:
                print(f"Creating new Pinecone index: {index_name}")
                self.pc.create_index(
                    name=index_name,
                    dimension=384,  # dimension for all-MiniLM-L6-v2
                    metric="cosine",
                    spec=pinecone.ServerlessSpec(cloud="aws", region="us-east-1")
                )
                print("Index created successfully!")
            else:
                print(f"Using existing Pinecone index: {index_name}")
        except Exception as e:
            print(f"Error checking/creating index: {str(e)}")
            print("Attempting to use existing index...")
            
        self.index = self.pc.Index(index_name)
        self.namespace = namespace
        
        # Initialize components
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.pdf_processor = PDFProcessor()
        
    def _chunk_text(self, text: str, chunk_size: Optional[int] = 50) -> List[str]:
        """Split text into chunks of approximately equal size.
        If chunk_size is None, return the entire text as a single chunk."""
        if chunk_size is None:
            return [text]
            
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        max_chunk_size = 1000  # Maximum characters per chunk
        
        for word in words:
            word_size = len(word) + 1  # +1 for space
            if current_size + word_size > max_chunk_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks
        
    def _extract_book_metadata(self, pdf_path: str, reader: PdfReader) -> Dict[str, Any]:
        """Extract metadata from the PDF book."""
        metadata = reader.metadata
        return {
            "title": metadata.get("/Title", Path(pdf_path).stem),
            "author": metadata.get("/Author", "Unknown"),
            "subject": metadata.get("/Subject", ""),
            "keywords": metadata.get("/Keywords", ""),
            "creator": metadata.get("/Creator", ""),
            "producer": metadata.get("/Producer", ""),
            "num_pages": len(reader.pages),
            "filename": Path(pdf_path).name
        }
        
    def vectorize_book(self, pdf_path: str, chunk_size: Optional[int] = 50) -> bool:
        """Process and vectorize a book, storing it in the vector database."""
        try:
            # Process PDF using PDFProcessor
            pdf_data = self.pdf_processor.process_pdf(pdf_path)
            if not pdf_data['text_content'] and not pdf_data['images']:
                print("No content extracted from PDF")
                return False
                
            # Extract metadata
            reader = PdfReader(pdf_path)
            metadata = self._extract_book_metadata(pdf_path, reader)
            
            success = True
            
            # Process text content
            if pdf_data['text_content']:
                try:
                    # Split into chunks
                    chunks = self._chunk_text(pdf_data['text_content'], chunk_size)
                    
                    # Generate embeddings and store text chunks
                    vectors = []
                    batch_size = 10  # Smaller batch size
                    
                    for i, chunk in enumerate(chunks):
                        try:
                            # Generate embedding
                            embedding = self.embedding_model.encode(chunk)
                            
                            # Create vector with metadata
                            vector = {
                                "id": f"{metadata['title']}_text_{i}",
                                "values": embedding.tolist(),
                                "metadata": {
                                    "title": metadata['title'],
                                    "author": metadata['author'],
                                    "chunk_index": i,
                                    "total_chunks": len(chunks),
                                    "content": chunk[:200] + "..." if len(chunk) > 200 else chunk,  # Further limit content size
                                    "type": "text"
                                }
                            }
                            vectors.append(vector)
                            
                            # Upload in smaller batches
                            if len(vectors) >= batch_size:
                                try:
                                    self.index.upsert(vectors=vectors, namespace=self.namespace)
                                    print(f"Uploaded batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}")
                                except Exception as e:
                                    print(f"Error uploading batch: {str(e)}")
                                    # Try uploading one by one
                                    for v in vectors:
                                        try:
                                            self.index.upsert(vectors=[v], namespace=self.namespace)
                                        except Exception as e2:
                                            print(f"Error uploading vector {v['id']}: {str(e2)}")
                                vectors = []
                                
                        except Exception as e:
                            print(f"Error processing chunk {i}: {str(e)}")
                            continue
                            
                    # Upload any remaining vectors
                    if vectors:
                        try:
                            self.index.upsert(vectors=vectors, namespace=self.namespace)
                        except Exception as e:
                            print(f"Error uploading final batch: {str(e)}")
                            # Try uploading one by one
                            for v in vectors:
                                try:
                                    self.index.upsert(vectors=[v], namespace=self.namespace)
                                except Exception as e2:
                                    print(f"Error uploading final vector {v['id']}: {str(e2)}")
                        
                    print(f"Successfully vectorized text content: {len(chunks)} chunks")
                except Exception as e:
                    print(f"Error processing text content: {str(e)}")
                    success = False
            
            # Process images separately
            if pdf_data['images']:
                try:
                    print(f"\nProcessing {len(pdf_data['images'])} images...")
                    for i, image_data in enumerate(pdf_data['images']):
                        try:
                            # Generate embedding for OCR text
                            ocr_text = image_data['ocr_text']
                            if ocr_text:
                                embedding = self.embedding_model.encode(ocr_text)
                                
                                # Create vector with metadata
                                vector = {
                                    "id": f"{metadata['title']}_image_{i}",
                                    "values": embedding.tolist(),
                                    "metadata": {
                                        "title": metadata['title'],
                                        "author": metadata['author'],
                                        "page_number": image_data['page_number'],
                                        "ocr_text": ocr_text[:200] + "..." if len(ocr_text) > 200 else ocr_text,
                                        "type": "image"
                                    }
                                }
                                
                                # Upload vector
                                self.index.upsert(vectors=[vector], namespace=self.namespace)
                                print(f"Processed image {i+1}/{len(pdf_data['images'])}")
                        except Exception as e:
                            print(f"Error processing image {i}: {str(e)}")
                            continue
                except Exception as e:
                    print(f"Error processing images: {str(e)}")
                    success = False
            
            return success
            
        except Exception as e:
            print(f"Error vectorizing book: {str(e)}")
            return False
            
    def search_book_content(self, query: str, top_k: int = 5, content_type: str = "all") -> List[Dict[str, Any]]:
        """Search for relevant content across all books."""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query)
            
            # Prepare filter based on content type
            filter_dict = {}
            if content_type == "text":
                filter_dict = {"type": "text"}
            elif content_type == "image":
                filter_dict = {"type": "image"}
                
            # Search the index
            results = self.index.query(
                vector=query_embedding.tolist(),
                top_k=top_k,
                include_metadata=True,
                namespace=self.namespace,
                filter=filter_dict if filter_dict else None
            )
            
            return results.matches
            
        except Exception as e:
            print(f"Error searching books: {str(e)}")
            return []
            
    def get_book_info(self, title: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific book."""
        try:
            # Search for any chunk from the book
            results = self.index.query(
                vector=[0.0] * 384,  # dummy vector
                filter={"title": title},
                top_k=1,
                include_metadata=True,
                namespace=self.namespace
            )
            
            if results.matches:
                return results.matches[0].metadata
            return None
            
        except Exception as e:
            print(f"Error getting book info: {str(e)}")
            return None
            
    def get_book_images(self, title: str) -> List[Dict[str, Any]]:
        """Get all images from a specific book."""
        try:
            # Search for image vectors from the book
            results = self.index.query(
                vector=[0.0] * 384,  # dummy vector
                filter={"title": title, "type": "image"},
                top_k=100,  # Adjust based on expected maximum images
                include_metadata=True,
                namespace=self.namespace
            )
            
            return [match.metadata for match in results.matches]
            
        except Exception as e:
            print(f"Error getting book images: {str(e)}")
            return []

    def store_image_data(self, image_info: Dict[str, Any]) -> bool:
        """Store image data in the vector database."""
        try:
            # Convert image data to base64 for storage
            if isinstance(image_info['image_data'], bytes):
                image_data_b64 = base64.b64encode(image_info['image_data']).decode('utf-8')
            else:
                image_data_b64 = base64.b64encode(image_info['image_data'].encode()).decode('utf-8')

            # Create vector with metadata
            vector = {
                "id": f"{image_info['file_name']}_image_{image_info['page_number']}",
                "values": self.embedding_model.encode(image_info.get('diagnosis', '')).tolist(),
                "metadata": {
                    "file_name": image_info['file_name'],
                    "page_number": image_info['page_number'],
                    "type": "image",
                    "image_data": image_data_b64,
                    "diagnosis": image_info.get('diagnosis', ''),
                    "ocr_text": image_info.get('ocr_text', '')
                }
            }
            
            # Upload vector
            self.index.upsert(vectors=[vector], namespace=self.namespace)
            return True
            
        except Exception as e:
            print(f"Error storing image data: {str(e)}")
            return False

    def search_image_content(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant images."""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query)
            
            # Search the index
            results = self.index.query(
                vector=query_embedding.tolist(),
                top_k=top_k,
                include_metadata=True,
                namespace=self.namespace,
                filter={"type": "image"}
            )
            
            # Decode base64 image data
            for match in results.matches:
                if 'image_data' in match.metadata:
                    match.metadata['image_data'] = base64.b64decode(match.metadata['image_data'])
            
            return results.matches
            
        except Exception as e:
            print(f"Error searching images: {str(e)}")
            return [] 