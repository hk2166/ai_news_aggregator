from flask import Flask, render_template
from app.services.article_service import get_recent_articles

app = Flask(__name__)

@app.route('/')
def index():
    articles = get_recent_articles(limit=50)
    return render_template('index.html', articles=articles)

if __name__ == '__main__':
    print("🚀 Starting web server at http://localhost:8000")
    app.run(debug=True, port=8000)
