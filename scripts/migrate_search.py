#!/usr/bin/env python
"""Database migration to add search features."""
import sys
import os

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.models.base import SessionLocal
from app.services.search_service import update_search_vectors


def migrate():
    print("🔧 Adding search features to database...")
    db = SessionLocal()
    
    try:
        # First, create all tables if they don't exist
        print("📦 Creating database tables...")
        from app.models.base import Base, engine
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created")
        
        # Add columns
        print("📝 Adding columns...")
        db.execute(text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS search_vector tsvector"))
        db.execute(text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0"))
        db.commit()
        print("✅ Columns added")
        
        # Create indexes
        print("📊 Creating indexes...")
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_article_search ON articles USING gin(search_vector)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_article_published ON articles(published_at)"))
        db.commit()
        print("✅ Indexes created")
        
        # Update search vectors
        print("🔍 Updating search vectors...")
        update_search_vectors(db)
        print("✅ Search vectors updated")
        
        # Create trigger
        print("⚡ Creating trigger...")
        db.execute(text("""
            CREATE OR REPLACE FUNCTION articles_search_vector_update() 
            RETURNS trigger AS $$
            BEGIN
                NEW.search_vector :=
                    setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                    setweight(to_tsvector('english', COALESCE(NEW.summary, '')), 'B') ||
                    setweight(to_tsvector('english', COALESCE(NEW.content_text, '')), 'C');
                RETURN NEW;
            END
            $$ LANGUAGE plpgsql
        """))
        db.execute(text("DROP TRIGGER IF EXISTS articles_search_vector_trigger ON articles"))
        db.execute(text("""
            CREATE TRIGGER articles_search_vector_trigger
                BEFORE INSERT OR UPDATE OF title, summary, content_text
                ON articles FOR EACH ROW
                EXECUTE FUNCTION articles_search_vector_update()
        """))
        db.commit()
        print("✅ Trigger created")
        
        # Verify
        result = db.execute(text("""
            SELECT COUNT(*) as total, COUNT(search_vector) as with_search, SUM(view_count) as total_views
            FROM articles
        """)).fetchone()
        
        print(f"\n📊 Summary:")
        print(f"   Total articles: {result[0]}")
        print(f"   With search vectors: {result[1]}")
        print(f"   Total views: {result[2] or 0}")
        print("\n✨ Migration completed!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
