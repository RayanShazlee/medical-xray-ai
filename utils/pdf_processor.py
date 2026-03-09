import os
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import io
from typing import List, Dict, Any, Tuple
import tempfile
import cv2
import numpy as np

class PDFProcessor:
    def __init__(self):
        # Ensure Tesseract is installed
        if os.name == 'nt':  # Windows
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    def preprocess_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """Preprocess image to improve OCR accuracy."""
        # Convert PIL Image to OpenCV format
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to preprocess the image
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # Apply dilation to connect text components
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
        gray = cv2.dilate(gray, kernel, iterations=1)
        
        # Convert back to PIL Image
        return Image.fromarray(gray)

    def extract_text_and_images(self, pdf_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Extract text and images from a PDF file
        Returns: Tuple of (text_content, list of image data)
        """
        text_content = ""
        images_data = []
        
        try:
            # Extract text from PDF
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                try:
                    text_content += page.extract_text() + "\n"
                except Exception as e:
                    print(f"Warning: Could not extract text from page: {str(e)}")
            
            # Convert PDF to images
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    images = convert_from_path(pdf_path, output_folder=temp_dir)
                except Exception as e:
                    print(f"Warning: Could not convert PDF to images: {str(e)}")
                    return text_content, images_data
                
                for i, image in enumerate(images):
                    try:
                        # Convert PIL image to bytes
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format='PNG')
                        img_byte_arr = img_byte_arr.getvalue()
                        
                        # Preprocess image for better OCR
                        processed_image = self.preprocess_image_for_ocr(image)
                        
                        # Extract text from image using OCR with improved settings
                        ocr_text = pytesseract.image_to_string(
                            processed_image,
                            config='--psm 3 --oem 3'  # Automatic page segmentation with OEM LSTM
                        )
                        
                        # Store image data
                        image_data = {
                            'page_number': i + 1,
                            'image_data': img_byte_arr,
                            'ocr_text': ocr_text.strip(),
                            'format': 'PNG'
                        }
                        images_data.append(image_data)
                    except Exception as e:
                        print(f"Warning: Could not process image {i+1}: {str(e)}")
                        continue
            
            return text_content.strip(), images_data
            
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            return "", []
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process a PDF file and return structured data
        """
        if not os.path.exists(pdf_path):
            print(f"Error: PDF file not found at {pdf_path}")
            return {'text_content': '', 'images': [], 'metadata': {}}
            
        text_content, images_data = self.extract_text_and_images(pdf_path)
        
        # Get PDF metadata
        try:
            reader = PdfReader(pdf_path)
            metadata = reader.metadata
            total_pages = len(reader.pages)
        except Exception as e:
            print(f"Warning: Could not extract PDF metadata: {str(e)}")
            metadata = {}
            total_pages = len(images_data)
        
        return {
            'text_content': text_content,
            'images': images_data,
            'metadata': {
                'file_name': os.path.basename(pdf_path),
                'total_pages': total_pages,
                'file_type': 'PDF',
                'title': metadata.get('/Title', ''),
                'author': metadata.get('/Author', ''),
                'subject': metadata.get('/Subject', ''),
                'keywords': metadata.get('/Keywords', '')
            }
        } 