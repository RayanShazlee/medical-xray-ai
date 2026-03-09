import pinecone
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
from typing import Dict, Any, List
import base64
import json

load_dotenv()

class VectorStore:
    def __init__(self):
        # Initialize Pinecone with new API
        self.pc = pinecone.Pinecone(
            api_key=os.getenv("PINECONE_API_KEY")
        )
        
        # Check if index exists
        existing_indexes = self.pc.list_indexes().names()
        if "book-knowledge" not in existing_indexes:
            print("Creating new Pinecone index...")
            self.pc.create_index(
                name="book-knowledge",
                dimension=384,  # sentence-transformers dimension
                metric="cosine",
                spec=pinecone.ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            print("Index created successfully!")
        else:
            print("Using existing Pinecone index")
            
        self.index = self.pc.Index("book-knowledge")
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using sentence-transformers."""
        return self.embedding_model.encode(text).tolist()
    
    def store_image(self, image_path: str, image_data: Dict[str, Any]) -> bool:
        """Store image data in vector store."""
        try:
            # Extract OCR text from image data
            ocr_text = ""
            if isinstance(image_data, dict) and 'features' in image_data:
                # If we have features, we can use them to generate a description
                ocr_text = "Medical image with extracted features"
            
            # Generate embedding for OCR text
            ocr_embedding = self.generate_embedding(ocr_text)
            
            # Store image reference (not the full base64 to avoid exceeding
            # Pinecone's 40KB metadata limit)
            self.index.upsert(
                vectors=[{
                    "id": f"image_{os.path.basename(image_path)}",
                    "values": ocr_embedding,
                    "metadata": {
                        "type": "image",
                        "filename": os.path.basename(image_path),
                        "ocr_text": ocr_text
                    }
                }]
            )
            
            return True
            
        except Exception as e:
            print(f"Error storing image: {str(e)}")
            return False
    
    def store_pdf_data(self, pdf_data: Dict[str, Any]) -> None:
        """Store PDF data in vector store."""
        try:
            # Generate embedding for text content
            text_embedding = self.generate_embedding(pdf_data["text_content"])
            
            # Store text content
            self.index.upsert(
                vectors=[{
                    "id": f"text_{pdf_data['metadata']['file_name']}",
                    "values": text_embedding,
                    "metadata": {
                        "type": "text",
                        "filename": pdf_data["metadata"]["file_name"],
                        "content": pdf_data["text_content"]
                    }
                }]
            )
            
            # Store images
            for i, image_data in enumerate(pdf_data["images"]):
                # Convert image data to base64
                image_base64 = base64.b64encode(image_data["image_data"]).decode("utf-8")
                
                # Generate embedding for OCR text
                ocr_embedding = self.generate_embedding(image_data["ocr_text"])
                
                # Store image data
                self.index.upsert(
                    vectors=[{
                        "id": f"image_{pdf_data['metadata']['file_name']}_{i}",
                        "values": ocr_embedding,
                        "metadata": {
                            "type": "image",
                            "filename": pdf_data["metadata"]["file_name"],
                            "image_data": image_base64,
                            "ocr_text": image_data["ocr_text"],
                            "page_number": image_data["page_number"]
                        }
                    }]
                )
                
        except Exception as e:
            print(f"Error storing PDF data: {str(e)}")
            raise
            
    def query_similar(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Query vector store for similar content."""
        try:
            # Generate embedding for query
            query_embedding = self.generate_embedding(query)
            
            # Query index — books are stored in the "books" namespace
            results = self.index.query(
                vector=query_embedding,
                top_k=k,
                include_metadata=True,
                namespace="books"
            )
            
            return results.matches
            
        except Exception as e:
            print(f"Error querying vector store: {str(e)}")
            raise 