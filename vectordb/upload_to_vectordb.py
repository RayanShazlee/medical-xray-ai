from book_vectordb import BookVectorDB
import argparse
from pathlib import Path
import os
from utils.pdf_processor import PDFProcessor
from utils.image_processing import process_image
from agents.radiologist_agent import RadiologistAgent
import tempfile

# Fixed paths
BASE_DIR = Path(__file__).parent.parent
PDF_DIR = BASE_DIR / "uploads"
BOOKS_DIR = BASE_DIR / "books"

def ensure_directories():
    """Ensure required directories exist."""
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)

def upload_book(vector_db: BookVectorDB, pdf_path: str, chunk_size: int, analyze_images: bool = True) -> None:
    """Upload a single book to the vector database with optional image analysis."""
    print(f"\nProcessing: {Path(pdf_path).name}")
    
    # Initialize components
    pdf_processor = PDFProcessor()
    radiologist_agent = RadiologistAgent() if analyze_images else None
    
    # Process PDF
    pdf_data = pdf_processor.process_pdf(pdf_path)
    
    if not pdf_data['text_content'] and not pdf_data['images']:
        print("No content extracted from PDF")
        return
    
    # Process text content
    if pdf_data['text_content']:
        success = vector_db.vectorize_book(pdf_path, chunk_size)
        if success:
            print("Text content processed and stored successfully!")
        else:
            print("Failed to process text content")
    
    # Process images if enabled
    if analyze_images and pdf_data['images']:
        print(f"\nProcessing {len(pdf_data['images'])} images...")
        for i, image_data in enumerate(pdf_data['images'], 1):
            temp_path = None
            try:
                # Save image temporarily
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    temp_file.write(image_data['image_data'])
                    temp_path = temp_file.name
                
                # Process image
                processed_image = process_image(temp_path)
                
                # Get medical analysis
                diagnosis = radiologist_agent.analyze_image(processed_image)
                
                # Store image data in vector store
                vector_db.store_image_data({
                    'file_name': Path(pdf_path).name,
                    'page_number': i,
                    'image_data': processed_image,
                    'diagnosis': diagnosis
                })
                
                print(f"Image {i}/{len(pdf_data['images'])} processed successfully")
                
            except Exception as e:
                print(f"Error processing image {i}: {str(e)}")
            finally:
                # Clean up temporary file
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)

def upload_all_books(vector_db: BookVectorDB, chunk_size: int, analyze_images: bool = True) -> None:
    """Upload all PDF books from the books directory with optional image analysis."""
    if not BOOKS_DIR.exists():
        print(f"Books directory not found at: {BOOKS_DIR}")
        print("Please add your PDF books to this directory.")
        return
        
    pdf_files = list(BOOKS_DIR.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in: {BOOKS_DIR}")
        print("Please add your PDF books to this directory.")
        return
        
    print(f"Found {len(pdf_files)} PDF files to process")
    for pdf_path in pdf_files:
        upload_book(vector_db, str(pdf_path), chunk_size, analyze_images)

def search_books(vector_db: BookVectorDB, query: str, top_k: int, search_type: str = 'all') -> None:
    """Search through all books in the database."""
    print(f"\nSearching for: {query}")
    
    if search_type in ['all', 'text']:
        text_results = vector_db.search_book_content(query, top_k)
        if text_results:
            print("\nText Results:")
            for i, match in enumerate(text_results, 1):
                metadata = match.metadata
                print(f"\n{i}. Book: {metadata['title']} (Page chunk {metadata['chunk_index'] + 1}/{metadata['total_chunks']})")
                print(f"   Author: {metadata['author']}")
                print(f"   Relevance score: {match.score:.4f}")
                print(f"   Content: {metadata['content'][:200]}...")
    
    if search_type in ['all', 'image']:
        image_results = vector_db.search_image_content(query, top_k)
        if image_results:
            print("\nImage Results:")
            for i, match in enumerate(image_results, 1):
                metadata = match.metadata
                print(f"\n{i}. Book: {metadata['file_name']}")
                print(f"   Page: {metadata['page_number']}")
                print(f"   Relevance score: {match.score:.4f}")
                print(f"   Diagnosis: {metadata['diagnosis']}")

def get_book_info(vector_db: BookVectorDB, title: str) -> None:
    """Get information about a specific book."""
    print(f"\nGetting info for book: {title}")
    info = vector_db.get_book_info(title)
    
    if not info:
        print("Book not found.")
        return
        
    print("\nBook Information:")
    print(f"Title: {info['title']}")
    print(f"Author: {info['author']}")
    print(f"Subject: {info['subject']}")
    print(f"Keywords: {info['keywords']}")
    print(f"Number of pages: {info['num_pages']}")
    print(f"Filename: {info['filename']}")
    
    # Get image information if available
    image_info = vector_db.get_book_images(title)
    if image_info:
        print("\nImage Information:")
        print(f"Total images: {len(image_info)}")
        for img in image_info:
            print(f"\nPage {img['page_number']}:")
            print(f"Diagnosis: {img['diagnosis']}")

def main():
    # Ensure directories exist
    ensure_directories()
    
    parser = argparse.ArgumentParser(description='Book Vector Database Tool')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload books to the vector database')
    upload_parser.add_argument('--chunk-size', type=int, default=100, const=None, nargs='?',
                             help='Size of text chunks for vectorization')
    upload_parser.add_argument('--no-images', action='store_true',
                             help='Skip image analysis during upload')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search through books')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--top-k', type=int, default=5,
                             help='Number of results to return')
    search_parser.add_argument('--type', choices=['all', 'text', 'image'],
                             default='all', help='Type of content to search')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Get information about a book')
    info_parser.add_argument('title', help='Book title')
    
    args = parser.parse_args()
    
    # Initialize vector database
    vector_db = BookVectorDB()
    
    if args.command == 'upload':
        # Upload all books from the books directory
        upload_all_books(vector_db, args.chunk_size, not args.no_images)
    elif args.command == 'search':
        search_books(vector_db, args.query, args.top_k, args.type)
    elif args.command == 'info':
        get_book_info(vector_db, args.title)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 