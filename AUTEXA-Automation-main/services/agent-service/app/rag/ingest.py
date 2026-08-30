import os
import sys
import glob
from pathlib import Path

# Add the app directory to sys.path so we can import app modules
sys.path.append(str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
# Load root or local .env
load_dotenv(Path(__file__).resolve().parents[3] / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.db.session import SessionLocal, engine
from app.models.knowledge_base_chunk import KnowledgeBaseChunk
from app.rag.embeddings import get_embedding
from sqlalchemy import text

def chunk_markdown(content: str) -> list[str]:
    """Splits markdown files into chunks by main headers (# or ##) to keep semantic contexts intact."""
    sections = []
    current_section = []
    
    for line in content.split('\n'):
        # Check if line is a header
        if line.startswith('#'):
            if current_section:
                sections.append('\n'.join(current_section).strip())
                current_section = []
        current_section.append(line)
        
    if current_section:
        sections.append('\n'.join(current_section).strip())
        
    # Filter out empty or very short sections
    return [s for s in sections if len(s.strip()) > 30]

def main():
    db = SessionLocal()
    try:
        from app.models import Base
        Base.metadata.create_all(bind=engine)
        # Check database connection and ensure extension exists
        with engine.connect() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
                print("Vector extension checked/installed successfully.")
            except Exception as ext_err:
                print(f"Notice: Vector extension might not be supported/installed: {ext_err}")
            
        print("Clearing existing knowledge base chunks...")
        db.query(KnowledgeBaseChunk).delete()
        db.commit()
        
        # Locate markdown files per tenant folder
        kb_path = Path(os.environ.get("KB_PATH", "/knowledge-base"))
        print(f"Scanning tenant directories in: {kb_path}")
        
        # Get all subdirectories (each corresponds to a tenant_id)
        tenant_dirs = []
        if kb_path.exists():
            tenant_dirs = [d for d in kb_path.iterdir() if d.is_dir()]
        
        if not tenant_dirs:
            print("No tenant subdirectories found. Processing root directory as 'autexa'...")
            tenant_dirs = [kb_path]
            
        for tenant_dir in tenant_dirs:
            tenant_id = tenant_dir.name if tenant_dir != kb_path else "autexa"
            if tenant_id.startswith(".") or tenant_id == "__pycache__":
                continue
                
            print(f"\nIngesting knowledge base for tenant: {tenant_id}...")
            md_files = glob.glob(str(tenant_dir / "*.md"))
            
            if not md_files:
                print(f"No markdown files found for tenant: {tenant_id}")
                continue
                
            for file_path in md_files:
                file_name = Path(file_path).name
                print(f"  Processing {file_name}...")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                chunks = chunk_markdown(content)
                print(f"  Generated {len(chunks)} chunks from {file_name}")
                
                for i, chunk in enumerate(chunks):
                    print(f"    Embedding chunk {i+1}/{len(chunks)}...")
                    embedding = get_embedding(chunk)
                    kb_chunk = KnowledgeBaseChunk(
                        tenant_id=tenant_id,
                        source_doc=file_name,
                        content=chunk,
                        embedding=embedding
                    )
                    db.add(kb_chunk)
                db.commit()
            
        print("\nIngestion completed successfully!")
    except Exception as e:
        print(f"Ingestion failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
