from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from src.components.linkedin import extract_jd
from src.components.websearch import analyze_company

load_dotenv()

app = Flask(__name__)

@app.route('/')
@app.route('/home')
def home():
    return render_template('landing_page.html', active='home')

@app.route('/components')
def components():
    return render_template('components.html', active='components')

@app.route('/workflows')
def workflows():
    return render_template('workflows.html', active='workflows')

@app.route('/components/linkedin')
def linkedin_component():
    return render_template('linkedin.html', active='components')

@app.route('/components/websearch')
def websearch_component():
    return render_template('websearch.html', active='components')

@app.route('/api/websearch/analyze', methods=['POST'])
def websearch_analyze():
    data = request.get_json()
    company = (data or {}).get('company', '').strip()
    title = (data or {}).get('title', '').strip()
    location = (data or {}).get('location', '').strip()
    jd = (data or {}).get('jd', '').strip()
    if not company:
        return jsonify({'success': False, 'error': 'Company name is required'})
    try:
        analysis = analyze_company(company, title, location, jd)
        return jsonify({'success': True, 'analysis': analysis})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/linkedin/extract', methods=['POST'])
def linkedin_extract():
    data = request.get_json()
    url = (data or {}).get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'})
    try:
        jd = extract_jd(url)
        return jsonify({'success': True, 'jd': jd})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=7200)
