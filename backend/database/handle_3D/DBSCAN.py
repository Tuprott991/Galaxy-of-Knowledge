from sklearn.cluster import DBSCAN
import numpy as np
import json
import psycopg2
import os
import uuid
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

def fetch_coordinates_from_db():
    """Fetch UMAP coordinates from PostgreSQL"""
    conn = get_db_connection()
    if not conn:
        return None, None
    
    try:
        cursor = conn.cursor()
        
        # Simple query - get paper_id and separate x,y,z coordinates
        query = """
        SELECT paper_id, plot_visualize_x, plot_visualize_y, plot_visualize_z
        FROM papers 
        WHERE plot_visualize_x IS NOT NULL 
          AND plot_visualize_y IS NOT NULL 
          AND plot_visualize_z IS NOT NULL
        ORDER BY paper_id
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        coordinates = []
        paper_ids = []
        
        for row in rows:
            paper_id, x, y, z = row
            coordinates.append([x, y, z])
            paper_ids.append(paper_id)
        
        cursor.close()
        conn.close()
        
        return np.array(coordinates), paper_ids
    
    except Exception as e:
        print(f"Error fetching coordinates: {e}")
        if conn:
            conn.close()
        return None, None

def generate_cluster_uuids(labels):
    """Generate UUIDs for each unique cluster"""
    unique_labels = set(labels)
    cluster_uuid_map = {}
    
    for cluster_id in unique_labels:
        if cluster_id == -1:
            # Use -1 for noise points
            cluster_uuid_map[cluster_id] = -1
        else:
            # Generate unique UUID for each cluster
            cluster_uuid_map[cluster_id] = str(uuid.uuid4())
    
    return cluster_uuid_map

def create_clustered_collection(coordinates, labels, paper_ids, cluster_uuid_map):
    """Create collection with cluster UUIDs for frontend"""
    clustered_papers = []
    
    for i, (paper_id, label) in enumerate(zip(paper_ids, labels)):
        x, y, z = coordinates[i]
        cluster_uuid = cluster_uuid_map[label]
        
        paper = {
            'paper_id': paper_id,
            'cluster_uuid': cluster_uuid,       # UUID or -1 for noise
            'position': {
                'x': float(x),
                'y': float(y), 
                'z': float(z)
            }
        }
        clustered_papers.append(paper)
    
    return clustered_papers

def analyze_clusters(coordinates, labels, cluster_uuid_map):
    """Analyze cluster statistics with UUIDs"""
    unique_labels = set(labels)
    cluster_stats = {}
    
    for cluster_id in unique_labels:
        cluster_mask = labels == cluster_id
        cluster_coords = coordinates[cluster_mask]
        cluster_uuid = cluster_uuid_map[cluster_id]
        
        if cluster_id == -1:
            # Noise points
            cluster_stats[cluster_uuid] = {
                'cluster_uuid': cluster_uuid,  # -1
                'count': len(cluster_coords),
                'type': 'noise'
            }
        else:
            # Regular clusters
            cluster_stats[cluster_uuid] = {
                'cluster_uuid': cluster_uuid,
                'count': len(cluster_coords),
                'centroid': np.mean(cluster_coords, axis=0).tolist(),
                'type': 'cluster'
            }
    
    return cluster_stats

def main():
    """Main function to run DBSCAN clustering and create collection with UUIDs"""
    print("Fetching coordinates from database...")
    coordinates, paper_ids = fetch_coordinates_from_db()
    
    if coordinates is None or len(coordinates) == 0:
        print("No coordinates found in database. Please run UMAP first.")
        return None
    
    print(f"Found {len(coordinates)} coordinate points")
    
    # Run DBSCAN clustering
    print("Running DBSCAN clustering...")
    clustering = DBSCAN(
        eps=0.5,
        min_samples=5,
        metric='euclidean'
    ).fit(coordinates)
    
    labels = clustering.labels_
    
    # Generate UUIDs for clusters
    cluster_uuid_map = generate_cluster_uuids(labels)
    
    # Analyze results
    unique_labels = set(labels)
    n_clusters = len(unique_labels) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    
    print(f"Number of clusters: {n_clusters}")
    print(f"Number of noise points: {n_noise}")
    
    # Create clustered collection with UUIDs
    clustered_papers = create_clustered_collection(coordinates, labels, paper_ids, cluster_uuid_map)
    
    # Analyze cluster statistics
    cluster_stats = analyze_clusters(coordinates, labels, cluster_uuid_map)
    
    # Create result object
    result = {
        'clustered_papers': clustered_papers,
        'cluster_info': cluster_stats,
        'cluster_uuid_map': cluster_uuid_map,
        'summary': {
            'total_papers': len(paper_ids),
            'n_clusters': n_clusters,
            'n_noise': n_noise
        }
    }
    
    print("DBSCAN clustering completed successfully!")
    
    # Print cluster summary
    print("\nCluster Summary:")
    for cluster_uuid, stats in cluster_stats.items():
        if stats['type'] == 'cluster':
            print(f"Cluster UUID {cluster_uuid[:8]}...: {stats['count']} papers")
        else:
            print(f"Noise points (cluster_uuid: -1): {stats['count']} papers")
    
    return result

if __name__ == "__main__":
    main()   
