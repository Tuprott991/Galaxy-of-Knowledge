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
        
        # Query from correct table name 'paper' (not 'papers')
        query = """
        SELECT paper_id, embeddings 
        FROM paper 
        WHERE embeddings IS NOT NULL
        ORDER BY paper_id
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        print(f"Found {len(rows)} papers with embeddings")
        
        embeddings = []
        paper_ids = []
        
        for i, row in enumerate(rows):
            paper_id, embedding_data = row
            try:
                # Handle vector type from PostgreSQL 
                if isinstance(embedding_data, str):
                    # Parse string representation of vector
                    if embedding_data.startswith('[') and embedding_data.endswith(']'):
                        embedding = np.array(json.loads(embedding_data))
                    else:
                        # Remove brackets and split by comma
                        clean_str = embedding_data.strip('[]')
                        embedding = np.array([float(x.strip()) for x in clean_str.split(',')])
                elif isinstance(embedding_data, list):
                    # Already a list
                    embedding = np.array(embedding_data)
                else:
                    # Try to convert directly
                    embedding = np.array(embedding_data)
                
                embeddings.append(embedding)
                paper_ids.append(paper_id)
                
                if (i + 1) % 100 == 0:
                    print(f"Processed {i + 1}/{len(rows)} embeddings...")
                    
            except Exception as e:
                print(f"Error parsing embedding for paper {paper_id}: {e}")
                continue
        
        cursor.close()
        conn.close()
        
        if embeddings:
            embeddings_array = np.array(embeddings)
            print(f"Successfully loaded {len(embeddings)} embeddings with shape {embeddings_array.shape}")
            return embeddings_array, paper_ids
        else:
            print("No valid embeddings found")
            return None, None
    
    except Exception as e:
        print(f"Error fetching embeddings: {e}")
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
        
        print(f"Updating {len(coordinates_data)} UMAP coordinates...")
        
        # Update coordinates in paper table (correct table name)
        for i, data in enumerate(coordinates_data):
            update_query = """
            UPDATE paper 
            SET plot_visualize_x = %s,
                plot_visualize_y = %s,
                plot_visualize_z = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE paper_id = %s
            """
            cursor.execute(update_query, (data['x'], data['y'], data['z'], data['paper_id']))
            
            if (i + 1) % 100 == 0:
                print(f"Updated {i + 1}/{len(coordinates_data)} coordinates...")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"Successfully updated {len(coordinates_data)} UMAP coordinates in database")
        return True
    
    except Exception as e:
        print(f"Error updating coordinates: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def main():
    """Main function to run UMAP analysis"""
    print("Starting UMAP Dimensionality Reduction")
    print("=" * 50)
    
    print("Fetching embeddings from database...")
    embeddings, paper_ids = fetch_embeddings_from_db()
    
    if embeddings is None or len(embeddings) == 0:
        print("No embeddings found in database")
        print("Please ensure papers have been inserted with embeddings first")
        return
    
    print(f"Found {len(embeddings)} embeddings with shape {embeddings.shape}")
    
    # Configure UMAP parameters based on data size
    n_neighbors = min(20, len(embeddings) - 1) if len(embeddings) > 20 else len(embeddings) - 1
    n_neighbors = max(2, n_neighbors)  # Ensure at least 2 neighbors
    
    print(f"UMAP Configuration:")
    print(f"   - n_neighbors: {n_neighbors}")
    print(f"   - min_dist: 0.2")
    print(f"   - n_components: 3 (3D visualization)")
    print(f"   - metric: cosine")
    
    # Run UMAP
    print("\nRunning UMAP dimensionality reduction...")
    umap_model = umap.UMAP(
        n_neighbors=n_neighbors,     
        min_dist=0.2,       
        n_components=3,    
        metric="cosine",
        random_state=42,
        verbose=True
    )
    
    coords = umap_model.fit_transform(embeddings)
    print(f"UMAP completed! Generated {coords.shape[0]} 3D coordinates")
    
    # Prepare data for database update
    print("\nPreparing coordinates for database update...")
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
        print("\nUMAP analysis completed successfully!")
        
        # Print sample results
        print("\nSample coordinates:")
        for i in range(min(5, len(coordinates_data))):
            data = coordinates_data[i]
            print(f"   Paper {data['paper_id']}: ({data['x']:.3f}, {data['y']:.3f}, {data['z']:.3f})")
        
        # Print statistics
        x_coords = [d['x'] for d in coordinates_data]
        y_coords = [d['y'] for d in coordinates_data]
        z_coords = [d['z'] for d in coordinates_data]
        
        print(f"\nCoordinate Statistics:")
        print(f"   X: [{min(x_coords):.3f}, {max(x_coords):.3f}]")
        print(f"   Y: [{min(y_coords):.3f}, {max(y_coords):.3f}]")
        print(f"   Z: [{min(z_coords):.3f}, {max(z_coords):.3f}]")
        
        print(f"\nReady for DBSCAN clustering!")
        print("Next step: Run DBSCAN.py to cluster the 3D coordinates")
        
    else:
        print("Failed to update database")

if __name__ == "__main__":
    main()


