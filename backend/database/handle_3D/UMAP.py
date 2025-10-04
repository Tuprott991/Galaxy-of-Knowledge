import umap
import numpy as np
import psycopg2
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Create database connection using environment variables"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=os.getenv('DB_PORT', 5432)
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def fetch_embeddings_from_db():
    """Fetch embeddings and paper IDs from PostgreSQL"""
    conn = get_db_connection()
    if not conn:
        return None, None
    
    try:
        cursor = conn.cursor()
        
        # Simple query - only get paper_id and embeddings
        query = """
        SELECT paper_id, embeddings 
        FROM papers 
        WHERE embeddings IS NOT NULL
        ORDER BY paper_id
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        embeddings = []
        paper_ids = []
        
        for row in rows:
            paper_id, embedding_str = row
            try:
                # Parse embeddings
                if embedding_str.startswith('[') and embedding_str.endswith(']'):
                    embedding = np.array(json.loads(embedding_str))
                else:
                    embedding = np.array([float(x) for x in embedding_str.split(',')])
                
                embeddings.append(embedding)
                paper_ids.append(paper_id)
            except Exception as e:
                print(f"Error parsing embedding for paper {paper_id}: {e}")
                continue
        
        cursor.close()
        conn.close()
        
        return np.array(embeddings), paper_ids
    
    except Exception as e:
        print(f"Error fetching data: {e}")
        if conn:
            conn.close()
        return None, None

def update_umap_coordinates(coordinates_data):
    """Update UMAP coordinates in database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Update coordinates in separate columns
        for data in coordinates_data:
            update_query = """
            UPDATE papers 
            SET plot_visualize_x = %s,
                plot_visualize_y = %s,
                plot_visualize_z = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE paper_id = %s
            """
            cursor.execute(update_query, (data['x'], data['y'], data['z'], data['paper_id']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"Successfully updated {len(coordinates_data)} UMAP coordinates")
        return True
    
    except Exception as e:
        print(f"Error updating coordinates: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def main():
    """Main function to run UMAP analysis"""
    print("Fetching embeddings from database...")
    embeddings, paper_ids = fetch_embeddings_from_db()
    
    if embeddings is None or len(embeddings) == 0:
        print("No embeddings found in database")
        return
    
    print(f"Found {len(embeddings)} embeddings with shape {embeddings.shape}")
    
    # Run UMAP
    print("Running UMAP dimensionality reduction...")
    umap_model = umap.UMAP(
        n_neighbors=min(20, len(embeddings) - 1),     
        min_dist=0.2,       
        n_components=3,    
        metric="cosine",
        random_state=42
    )
    
    coords = umap_model.fit_transform(embeddings)
    
    # Prepare data for database update
    coordinates_data = []
    for i, (x, y, z) in enumerate(coords):
        coordinates_data.append({
            "paper_id": paper_ids[i],
            "x": float(x),
            "y": float(y),
            "z": float(z)
        })
    
    # Update database
    print("Updating coordinates in database...")
    success = update_umap_coordinates(coordinates_data)
    
    if success:
        print("UMAP analysis completed successfully!")
        
        # Print sample results
        print("\nSample coordinates:")
        for i in range(min(5, len(coordinates_data))):
            data = coordinates_data[i]
            print(f"Paper {data['paper_id']}: ({data['x']:.3f}, {data['y']:.3f}, {data['z']:.3f})")
    else:
        print("Failed to update database")

if __name__ == "__main__":
    main()


