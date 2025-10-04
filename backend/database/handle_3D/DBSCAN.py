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
        
        # Query from correct table name 'paper' (not 'papers')
        query = """
        SELECT paper_id, plot_visualize_x, plot_visualize_y, plot_visualize_z
        FROM paper 
        WHERE plot_visualize_x IS NOT NULL 
          AND plot_visualize_y IS NOT NULL 
          AND plot_visualize_z IS NOT NULL
        ORDER BY paper_id
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        print(f"Found {len(rows)} papers with 3D coordinates")
        
        coordinates = []
        paper_ids = []
        
        for i, row in enumerate(rows):
            paper_id, x, y, z = row
            coordinates.append([float(x), float(y), float(z)])
            paper_ids.append(paper_id)
            
            if (i + 1) % 100 == 0:
                print(f"Processed {i + 1}/{len(rows)} coordinates...")
        
        cursor.close()
        conn.close()
        
        if coordinates:
            coordinates_array = np.array(coordinates)
            print(f"Successfully loaded {len(coordinates)} 3D coordinates with shape {coordinates_array.shape}")
            return coordinates_array, paper_ids
        else:
            print("No valid coordinates found")
            return None, None
    
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

def update_cluster_assignments(paper_ids, labels, cluster_uuid_map):
    """Update cluster assignments in database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        print(f"Updating {len(paper_ids)} cluster assignments...")
        
        # Update cluster assignments in paper table
        for i, (paper_id, label) in enumerate(zip(paper_ids, labels)):
            cluster_uuid = cluster_uuid_map[label]
            
            update_query = """
            UPDATE paper 
            SET cluster = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE paper_id = %s
            """
            cursor.execute(update_query, (str(cluster_uuid), paper_id))
            
            if (i + 1) % 100 == 0:
                print(f"Updated {i + 1}/{len(paper_ids)} cluster assignments...")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"Successfully updated {len(paper_ids)} cluster assignments in database")
        return True
    
    except Exception as e:
        print(f"Error updating cluster assignments: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

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
    print("Starting DBSCAN Clustering")
    print("=" * 50)
    
    print("Fetching 3D coordinates from database...")
    coordinates, paper_ids = fetch_coordinates_from_db()
    
    if coordinates is None or len(coordinates) == 0:
        print("No coordinates found in database")
        print("Please run UMAP.py first to generate 3D coordinates")
        return None
    
    print(f"Found {len(coordinates)} coordinate points with shape {coordinates.shape}")
    
    # Configure DBSCAN parameters based on data size
    eps = 0.5 if len(coordinates) > 100 else 0.3
    min_samples = min(5, max(2, len(coordinates) // 20))  # Adaptive min_samples
    
    print(f"DBSCAN Configuration:")
    print(f"   - eps: {eps}")
    print(f"   - min_samples: {min_samples}")
    print(f"   - metric: euclidean")
    
    # Run DBSCAN clustering
    print("\nRunning DBSCAN clustering...")
    clustering = DBSCAN(
        eps=eps,
        min_samples=min_samples,
        metric='euclidean'
    ).fit(coordinates)
    
    labels = clustering.labels_
    
    # Generate UUIDs for clusters
    cluster_uuid_map = generate_cluster_uuids(labels)
    
    # Analyze results
    unique_labels = set(labels)
    n_clusters = len(unique_labels) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    
    print(f"DBSCAN completed!")
    print(f"   - Number of clusters: {n_clusters}")
    print(f"   - Number of noise points: {n_noise}")
    print(f"   - Clustering ratio: {(len(coordinates) - n_noise)/len(coordinates)*100:.1f}%")
    
    # Update database with cluster assignments
    print("\nUpdating cluster assignments in database...")
    update_success = update_cluster_assignments(paper_ids, labels, cluster_uuid_map)
    
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
            'n_noise': n_noise,
            'clustering_ratio': (len(coordinates) - n_noise)/len(coordinates)*100
        }
    }
    
    if update_success:
        print("Database update completed successfully!")
    else:
        print("Database update failed, but clustering results are available")
    
    # Print cluster summary
    print("\nCluster Summary:")
    for cluster_uuid, stats in cluster_stats.items():
        if stats['type'] == 'cluster':
            print(f"   Cluster {cluster_uuid[:8]}...: {stats['count']} papers")
        else:
            print(f"   Noise points (cluster_uuid: -1): {stats['count']} papers")
    
    # Save results to JSON file
    output_file = "/home/nghia-duong/workspace/Galaxy-of-Knowledge/backend/clustering_results.json"
    try:
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nResults saved to: {output_file}")
    except Exception as e:
        print(f"Could not save results to file: {e}")
    
    print(f"\nDBSCAN clustering completed successfully!")
    print("Ready for frontend visualization!")
    
    return result

if __name__ == "__main__":
    main()   
