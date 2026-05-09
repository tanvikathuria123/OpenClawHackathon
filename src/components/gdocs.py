import os, re, json, io, shutil, subprocess, tempfile
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.file',
]
TOKEN_FILE = 'data/google_token.json'
CREDS_FILE = 'data/google_credentials.json'


def get_flow(redirect_uri):
    return Flow.from_client_secrets_file(
        CREDS_FILE, scopes=SCOPES, redirect_uri=redirect_uri,
        autogenerate_code_verifier=False
    )


def get_credentials():
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE) as f:
        granted = set(json.load(f).get('scopes', []))
    if not set(SCOPES).issubset(granted):
        return None
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    return creds if creds and creds.valid else None


def save_token(token_json):
    os.makedirs('data', exist_ok=True)
    with open(TOKEN_FILE, 'w') as f:
        f.write(token_json)


def latex_to_text(latex):
    text = re.sub(r'\\(documentclass|usepackage|begin|end|maketitle|newpage|hline|centering|label|ref|cite|bibliographystyle|bibliography)[^\n]*', '', latex)
    text = re.sub(r'\\(title|author|section|subsection|subsubsection|textbf|textit|underline|emph|caption|footnote)\{([^}]*)\}', r'\2', text)
    text = re.sub(r'\\item\s*', '• ', text)
    text = re.sub(r'\\\\', '\n', text)
    text = re.sub(r'\$\$([^$]+)\$\$', r'\1', text)
    text = re.sub(r'\$([^$]+)\$', r'\1', text)
    text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    text = re.sub(r'[{}]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def create_doc(title, latex_content):
    creds = get_credentials()
    service = build('docs', 'v1', credentials=creds)
    doc = service.documents().create(body={'title': title}).execute()
    doc_id = doc['documentId']
    text = latex_to_text(latex_content)
    if text:
        service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': [{'insertText': {'location': {'index': 1}, 'text': text}}]}
        ).execute()
    return f"https://docs.google.com/document/d/{doc_id}/edit"


def _tectonic_path():
    for c in [shutil.which('tectonic'),
              os.path.expanduser('~/.local/bin/tectonic'),
              '/opt/homebrew/bin/tectonic',
              '/usr/local/bin/tectonic']:
        if c and os.path.exists(c):
            return c
    raise RuntimeError("tectonic not found in PATH or ~/.local/bin/tectonic")


def compile_latex_to_pdf(latex_source):
    bin_path = _tectonic_path()
    with tempfile.TemporaryDirectory() as tmp:
        tex_path = os.path.join(tmp, 'resume.tex')
        with open(tex_path, 'w') as f:
            f.write(latex_source)
        result = subprocess.run(
            [bin_path, '-X', 'compile', tex_path, '--outdir', tmp],
            capture_output=True, text=True, timeout=180
        )
        if result.returncode != 0:
            log = (result.stderr or result.stdout or '')[-2000:]
            raise RuntimeError(f"LaTeX compilation failed:\n{log}")
        pdf_path = os.path.join(tmp, 'resume.pdf')
        if not os.path.exists(pdf_path):
            raise RuntimeError(f"tectonic produced no PDF. Log:\n{result.stdout[-1000:]}")
        with open(pdf_path, 'rb') as f:
            return f.read()


def upload_pdf_to_drive(title, pdf_bytes):
    creds = get_credentials()
    if not creds:
        raise RuntimeError("Google not authenticated — visit /components/gdocs to connect (re-auth required for new Drive scope)")
    drive = build('drive', 'v3', credentials=creds)
    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype='application/pdf')
    file = drive.files().create(
        body={'name': f'{title}.pdf'},
        media_body=media,
        fields='id, webViewLink'
    ).execute()
    return file['webViewLink']


def create_pdf_doc(title, latex_content):
    pdf_bytes = compile_latex_to_pdf(latex_content)
    return upload_pdf_to_drive(title, pdf_bytes)
