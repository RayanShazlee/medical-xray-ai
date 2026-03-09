import os
from typing import Dict, Any, List
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import io

class BookProcessor:
    def __init__(self, vector_store):
        self.vector_store = vector_store
        
    def process_book(self, pdf_path: str) -> Dict[str, Any]:
        """Process a PDF book and prepare it for vector store upload."""
        try:
            # Read PDF text
            reader = PdfReader(pdf_path)
            text_content = ""
            for page in reader.pages:
                text_content += page.extract_text() + "\n"
            
            # Convert PDF pages to images
            images = convert_from_path(pdf_path)
            
            # Process each image with OCR
            processed_images = []
            for i, image in enumerate(images):
                # Convert PIL Image to bytes
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                # Perform OCR
                ocr_text = pytesseract.image_to_string(image)
                
                processed_images.append({
                    "image": img_byte_arr,
                    "ocr_text": ocr_text,
                    "page_number": i + 1
                })
            
            # Prepare data for vector store
            book_data = {
                "text": text_content,
                "images": processed_images,
                "metadata": {
                    "filename": os.path.basename(pdf_path),
                    "total_pages": len(images),
                    "file_size": os.path.getsize(pdf_path)
                }
            }
            
            return book_data
            
        except Exception as e:
            print(f"Error processing book: {str(e)}")
            raise
            
    def upload_book(self, pdf_path: str) -> bool:
        """Process and upload a book to the vector store."""
        try:
            # Process the book
            book_data = self.process_book(pdf_path)
            
            # Upload to vector store
            self.vector_store.store_pdf_data(book_data)
            
            print(f"Successfully uploaded book: {book_data['metadata']['filename']}")
            return True
            
        except Exception as e:
            print(f"Error uploading book: {str(e)}")
            return False 