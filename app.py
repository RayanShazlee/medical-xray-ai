from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import os
import json
import datetime
from dotenv import load_dotenv
from agents.radiologist_agent import RadiologistAgent
from utils.image_processing import process_image
from utils.vector_store import VectorStore
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from utils.pdf_processor import PDFProcessor
from utils.report_history import ReportHistory
from utils.pdf_report_generator import PDFReportGenerator
from utils.dicom_processor import DICOMProcessor
import tempfile

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'medical-ai-secret-key')
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['REPORT_FOLDER'] = os.path.join('static', 'reports')
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'dcm', 'dicom'}

# Initialize SocketIO for real-time progress
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORT_FOLDER'], exist_ok=True)

# Initialize agents and services
radiologist_agent = RadiologistAgent()
vector_store = VectorStore()
pdf_processor = PDFProcessor()
report_history = ReportHistory()
pdf_report_gen = PDFReportGenerator()
dicom_processor = DICOMProcessor()

# Initialize Groq LLM for medical term explanations
term_llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",
    temperature=0.3
)
term_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a friendly medical educator who explains medical terms to patients in simple, 
easy-to-understand language. For each term, provide:
1. A one-sentence plain English definition
2. A brief "Why it matters" explanation (1-2 sentences about clinical relevance)
3. A "Think of it like..." analogy that a non-medical person can relate to
4. Related terms (2-3 related medical words the patient might also encounter)

Keep the tone warm, reassuring, and non-technical. Avoid medical jargon in your explanations.
Format your response as JSON with keys: "definition", "why_it_matters", "analogy", "related_terms" (array of strings), "pronunciation" (phonetic pronunciation guide)."""),
    ("human", "Please explain this medical term in simple language for a patient: {term}")
])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    # Serve React SPA if built, otherwise fall back to legacy template
    react_index = os.path.join(app.static_folder, 'react', 'index.html')
    if os.path.exists(react_index):
        return send_file(react_index)
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Get patient context from form
        patient_context = {}
        if request.form.get('patient_age'):
            try:
                patient_context['age'] = int(request.form['patient_age'])
            except ValueError:
                pass
        if request.form.get('patient_sex'):
            patient_context['sex'] = request.form['patient_sex']
        if request.form.get('patient_symptoms'):
            patient_context['symptoms'] = request.form['patient_symptoms']
        if request.form.get('symptom_duration'):
            patient_context['duration'] = request.form['symptom_duration']
        if request.form.get('smoking') == 'true':
            patient_context['smoking'] = True
        if request.form.get('immunocompromised') == 'true':
            patient_context['immunocompromised'] = True
        if request.form.get('comorbidities') == 'true':
            patient_context['comorbidities'] = True
        
        # Language selection
        language = request.form.get('language', 'en')
        
        try:
            if filename.lower().endswith('.pdf'):
                # Process PDF file
                pdf_data = pdf_processor.process_pdf(file_path)
                if pdf_data['text_content'] or pdf_data['images']:
                    if vector_store.store_pdf_data(pdf_data):
                        return jsonify({
                            'message': 'PDF processed and stored successfully',
                            'text_content': pdf_data['text_content'],
                            'total_images': len(pdf_data['images'])
                        })
                    else:
                        return jsonify({'error': 'Failed to store PDF data'}), 500
                else:
                    return jsonify({'error': 'No content extracted from PDF'}), 400
            
            elif filename.lower().endswith(('.dcm', '.dicom')):
                # Process DICOM file (Tier 2)
                dicom_data = dicom_processor.process(file_path)
                image = dicom_data['image']
                
                # Save as PNG for display
                png_filename = filename.rsplit('.', 1)[0] + '.png'
                png_path = os.path.join(app.config['UPLOAD_FOLDER'], png_filename)
                image.save(png_path)
                
                # Merge DICOM metadata into patient context
                dicom_meta = dicom_data.get('metadata', {})
                if not patient_context.get('age') and dicom_meta.get('PatientAgeYears'):
                    patient_context['age'] = dicom_meta['PatientAgeYears']
                if not patient_context.get('sex') and dicom_meta.get('PatientSex'):
                    patient_context['sex'] = dicom_meta['PatientSex']
                
                # Process like a regular image
                from utils.image_processing import enhance_xray, create_enhanced_comparison
                enhanced_image = enhance_xray(image)
                comparison_b64 = create_enhanced_comparison(image, enhanced_image)
                
                image_data = {
                    'original_path': png_path,
                    'image': image,
                    'enhanced_image': enhanced_image,
                    'comparison_b64': comparison_b64,
                    'size': image.size
                }
                
                def emit_progress(data):
                    socketio.emit('analysis_progress', data)
                
                result = radiologist_agent.analyze_image(
                    image_data, 
                    patient_context=patient_context if patient_context else None,
                    language=language,
                    emit_progress=emit_progress
                )
                
                response_data = _build_response(result, png_filename, patient_context, dicom_meta, language)
                return jsonify(response_data)
            
            else:
                # Process regular image file
                image_data = process_image(file_path)
                
                def emit_progress(data):
                    socketio.emit('analysis_progress', data)
                
                result = radiologist_agent.analyze_image(
                    image_data,
                    patient_context=patient_context if patient_context else None,
                    language=language,
                    emit_progress=emit_progress
                )
                
                response_data = _build_response(result, filename, patient_context, {}, language)
                
                # Store image in vector store
                vector_store.store_image(file_path, image_data)
                
                return jsonify(response_data)
        
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400


def _build_response(result, filename, patient_context, dicom_metadata, language):
    """Build the JSON response from analysis results and save to history."""
    if isinstance(result, dict):
        diagnosis = result.get('diagnosis', '')
        heatmap = result.get('heatmap')
        enhanced_comparison = result.get('enhanced_comparison')
        detections = result.get('detections')
        quality_report = result.get('quality_report')
        segmentation_overlay = result.get('segmentation_overlay')
        ctr = result.get('ctr', {})
        differentials = result.get('differentials', [])
        clinical_decision = result.get('clinical_decision', {})
        uncertainty = result.get('uncertainty', {})
        severity = result.get('severity')
        measurements = result.get('measurements', {})
    else:
        diagnosis = str(result)
        heatmap = enhanced_comparison = segmentation_overlay = None
        detections = differentials = []
        quality_report = ctr = clinical_decision = uncertainty = measurements = {}
        severity = None
    
    response_data = {
        'diagnosis': diagnosis,
        'image_path': f'/static/uploads/{filename}',
        'language': language
    }
    
    if heatmap:
        response_data['heatmap'] = heatmap
    if enhanced_comparison:
        response_data['enhanced_comparison'] = enhanced_comparison
    if detections:
        response_data['detections'] = detections
    if quality_report:
        response_data['quality_report'] = quality_report
    if segmentation_overlay:
        response_data['segmentation_overlay'] = segmentation_overlay
    if ctr:
        response_data['ctr'] = ctr
    if differentials:
        response_data['differentials'] = differentials
    if clinical_decision:
        response_data['clinical_decision'] = clinical_decision
    if uncertainty:
        response_data['uncertainty'] = uncertainty
    if severity:
        response_data['severity'] = severity
    if measurements:
        response_data['measurements'] = measurements
    if dicom_metadata:
        response_data['dicom_metadata'] = dicom_metadata
    
    # Save to report history
    try:
        history_data = {
            'image_filename': filename,
            'image_path': f'/static/uploads/{filename}',
            'diagnosis': diagnosis,
            'detections': detections or [],
            'quality_report': quality_report or {},
            'ctr': ctr or {},
            'differentials': differentials or [],
            'clinical_decision': clinical_decision or {},
            'severity': severity,
            'patient_context': patient_context or {},
            'dicom_metadata': dicom_metadata or {},
            'language': language
        }
        report_id = report_history.save_report(history_data)
        response_data['report_id'] = report_id
        print(f"📊 Report saved: {report_id}")
    except Exception as e:
        print(f"Warning: Could not save report to history: {e}")
    
    return response_data


@app.route('/export_pdf', methods=['POST'])
def export_pdf():
    """Export analysis results as a professional PDF report (Tier 4)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"radiology_report_{timestamp}.pdf"
        pdf_path = os.path.join(app.config['REPORT_FOLDER'], pdf_filename)
        
        pdf_report_gen.generate(data, pdf_path)
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=pdf_filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500


@app.route('/history', methods=['GET'])
def get_history():
    """Get report history (Tier 4)."""
    limit = request.args.get('limit', 20, type=int)
    reports = report_history.get_recent_reports(limit)
    return jsonify({'reports': reports})


@app.route('/history/<report_id>', methods=['GET'])
def get_report(report_id):
    """Get a specific report by ID."""
    report = report_history.get_report(report_id)
    if report:
        return jsonify(report)
    return jsonify({'error': 'Report not found'}), 404


@app.route('/history/search', methods=['POST'])
def search_history():
    """Search report history."""
    data = request.get_json()
    query = data.get('query', '')
    results = report_history.search_reports(query)
    return jsonify({'results': results})


@app.route('/dashboard', methods=['GET'])
def dashboard_stats():
    """Get dashboard statistics (Tier 4)."""
    stats = report_history.get_statistics()
    return jsonify(stats)


@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400
    
    query = data['query']
    try:
        results = vector_store.query_similar(query)
    except Exception as e:
        return jsonify({'error': f'Search failed: {str(e)}'}), 500
    
    formatted_results = []
    for match in results:
        result_type = match.metadata.get('type', 'text')
        result = {
            'score': match.score,
            'type': result_type
        }
        
        if result_type == 'text':
            result['content'] = match.metadata.get('content', '')
            result['title'] = match.metadata.get('title', '')
            result['author'] = match.metadata.get('author', '')
            result['chunk_index'] = match.metadata.get('chunk_index', '')
            result['total_chunks'] = match.metadata.get('total_chunks', '')
        elif result_type == 'image':
            result['page_number'] = match.metadata.get('page_number', '')
            result['ocr_text'] = match.metadata.get('ocr_text', '')
            result['image_data'] = match.metadata.get('image_data', '')
            result['filename'] = match.metadata.get('filename', '')
            result['title'] = match.metadata.get('title', '')
        
        formatted_results.append(result)
    
    return jsonify({'results': formatted_results})


@app.route('/explain-term', methods=['POST'])
def explain_term():
    """Use LLM to explain a medical term in patient-friendly language."""
    data = request.get_json()
    if not data or 'term' not in data:
        return jsonify({'error': 'No term provided'}), 400
    
    term = data['term'].strip()
    if not term or len(term) > 200:
        return jsonify({'error': 'Invalid term'}), 400

    try:
        import re
        chain = term_prompt | term_llm
        response = chain.invoke({"term": term})
        
        content = response.content.strip()
        
        # Strip markdown code fences: ```json ... ``` or ``` ... ```
        fence_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)```', content)
        if fence_match:
            content = fence_match.group(1).strip()
        
        # Try to find and parse the outermost JSON object using brace matching
        result = None
        start = content.find('{')
        if start != -1:
            depth = 0
            end = start
            for i in range(start, len(content)):
                if content[i] == '{':
                    depth += 1
                elif content[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            json_str = content[start:end]
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                # LLM sometimes returns unquoted values — try to fix common issues
                # Attempt: wrap unquoted string values in quotes
                try:
                    # Fix unquoted values after keys like "key": value\n
                    fixed = re.sub(
                        r'("(?:definition|why_it_matters|analogy|pronunciation)")\s*:\s*(?!")(.*?)(?=\n\s*"|$|\n\s*\})',
                        lambda m: f'{m.group(1)}: "{m.group(2).strip().rstrip(",")}"',
                        json_str,
                        flags=re.DOTALL
                    )
                    result = json.loads(fixed)
                except (json.JSONDecodeError, Exception):
                    result = None
        
        # If JSON parsing failed entirely, extract values with regex from the raw text
        if not result or not isinstance(result, dict):
            result = {}
            # Try to pull values by key name patterns from the raw LLM output
            for key in ['definition', 'why_it_matters', 'analogy', 'pronunciation']:
                pattern = rf'"{key}"\s*:\s*"?(.*?)(?:"\s*[,\}}]|(?=\n\s*"))'
                m = re.search(pattern, content, re.DOTALL)
                if m:
                    val = m.group(1).strip().strip('"').strip(',').strip()
                    result[key] = val
            
            # Extract related_terms array
            rt_match = re.search(r'"related_terms"\s*:\s*\[(.*?)\]', content, re.DOTALL)
            if rt_match:
                terms_raw = rt_match.group(1)
                result['related_terms'] = [t.strip().strip('"').strip("'") for t in terms_raw.split(',') if t.strip().strip('"').strip("'")]
            
            # If nothing was extracted, use the whole content as definition
            if not result.get('definition'):
                # Remove JSON-like noise from the content
                clean = re.sub(r'[{}"\\]', '', content)
                clean = re.sub(r'^\s*(definition|why_it_matters|analogy|related_terms|pronunciation)\s*:\s*', '', clean, flags=re.MULTILINE)
                result['definition'] = clean.strip() if clean.strip() else content
        
        # Ensure all expected keys exist
        result.setdefault('definition', '')
        result.setdefault('why_it_matters', '')
        result.setdefault('analogy', '')
        result.setdefault('related_terms', [])
        result.setdefault('pronunciation', '')
        
        # Ensure related_terms is a list of strings
        if isinstance(result['related_terms'], str):
            result['related_terms'] = [t.strip() for t in result['related_terms'].split(',') if t.strip()]
        
        result['term'] = term
        return jsonify(result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to explain term: {str(e)}'}), 500


# ===== WebSocket events for real-time progress (Tier 4) =====
@socketio.on('connect')
def handle_connect():
    print('Client connected for real-time progress')
    emit('connected', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7860))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    socketio.run(app, debug=debug, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)