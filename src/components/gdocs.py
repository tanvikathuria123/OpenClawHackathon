import os, re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/documents']
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
