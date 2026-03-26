from app.models.base import SessionLocal
from app.models.article import Article
from app.services.summarizer import process_article


def process_new_articles() -> dict:
    db = SessionLocal()
    processed = failed = 0

    try:
        pending = (
            db.query(Article)
            .filter(Article.is_processed == False, Article.content_text != None, Article.content_text != "")
            .all()
        )
        print(f"  {len(pending)} articles to process")

        for article in pending:
            result = process_article(article.title, article.content_text)
            if result["summary"]:
                article.summary = result["summary"]
                article.tags = result["tags"]
                article.is_processed = True
                db.commit()
                processed += 1
            else:
                failed += 1
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

    return {"processed": processed, "failed": failed}