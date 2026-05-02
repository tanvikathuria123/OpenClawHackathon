from flask import Flask, render_template

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

if __name__ == '__main__':
    app.run(debug=True, port=7200)
