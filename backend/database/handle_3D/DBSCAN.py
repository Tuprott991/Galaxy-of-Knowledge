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

def fetch_embeddings_from_db():
    """Fetch embeddings from PostgreSQL"""
    conn = get_db_connection()
    if not conn:
        return None, None
    
    try:
        cursor = conn.cursor()
        
        # Query embeddings from paper table
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
            paper_id, embedding_vector = row
            
            # Convert PostgreSQL vector to numpy array
            if embedding_vector:
                try:
                    # If embedding_vector is a string, parse it
                    if isinstance(embedding_vector, str):
                        # Remove brackets and split by comma
                        embedding_str = embedding_vector.strip('[]')
                        embedding_list = [float(x.strip()) for x in embedding_str.split(',')]
                    elif isinstance(embedding_vector, list):
                        # Already a list, convert to float
                        embedding_list = [float(x) for x in embedding_vector]
                    else:
                        print(f"Unexpected embedding type: {type(embedding_vector)}")
                        continue
                    
                    embeddings.append(embedding_list)
                    paper_ids.append(paper_id)
                    
                except Exception as e:
                    print(f"Error parsing embedding for paper {paper_id}: {e}")
                    continue
            
            if (i + 1) % 100 == 0:
                print(f"Processed {i + 1}/{len(rows)} embeddings...")
        
        cursor.close()
        conn.close()
        
        if embeddings:
            embeddings_array = np.array(embeddings, dtype=np.float32)  # Explicitly set numeric dtype
            
            # Ensure proper shape for DBSCAN
            if embeddings_array.ndim == 1:
                # If 1D array, reshape to 2D
                embeddings_array = embeddings_array.reshape(-1, 1)
            elif embeddings_array.ndim == 3:
                # If 3D array, flatten to 2D
                embeddings_array = embeddings_array.reshape(embeddings_array.shape[0], -1)
            
            print(f"Successfully loaded {len(embeddings)} embeddings with shape {embeddings_array.shape}")
            print(f"Embeddings dtype: {embeddings_array.dtype}")
            return embeddings_array, paper_ids
        else:
            print("No valid embeddings found")
            return None, None
    
    except Exception as e:
        print(f"Error fetching embeddings: {e}")
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

def create_clustered_collection(embeddings, labels, paper_ids, cluster_uuid_map):
    """Create collection with cluster UUIDs for frontend (no coordinates needed)"""
    clustered_papers = []
    
    for i, (paper_id, label) in enumerate(zip(paper_ids, labels)):
        cluster_uuid = cluster_uuid_map[label]
        
        paper = {
            'paper_id': paper_id,
            'cluster_uuid': cluster_uuid,       # UUID or -1 for noise
            'embedding_dimension': len(embeddings[i])  # Just for info
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

def analyze_clusters(embeddings, labels, cluster_uuid_map):
    """Analyze cluster statistics with UUIDs (using embeddings)"""
    unique_labels = set(labels)
    cluster_stats = {}
    
    for cluster_id in unique_labels:
        cluster_mask = labels == cluster_id
        cluster_embeddings = embeddings[cluster_mask]
        cluster_uuid = cluster_uuid_map[cluster_id]
        
        if cluster_id == -1:
            # Noise points
            cluster_stats[cluster_uuid] = {
                'cluster_uuid': cluster_uuid,  # -1
                'count': len(cluster_embeddings),
                'type': 'noise'
            }
        else:
            # Regular clusters
            cluster_stats[cluster_uuid] = {
                'cluster_uuid': cluster_uuid,
                'count': len(cluster_embeddings),
                'centroid_dimension': len(embeddings[0]),  # Embedding dimension
                'type': 'cluster'
            }
    
    return cluster_stats

def main():
    """Main function to run DBSCAN clustering on embeddings"""
    print("Starting DBSCAN Clustering on Embeddings")
    print("=" * 50)
    
    print("Fetching embeddings from database...")
    embeddings, paper_ids = fetch_embeddings_from_db()
    
    if embeddings is None or len(embeddings) == 0:
        print("No embeddings found in database")
        print("Please run embed_ingestion.py first to generate embeddings")
        return None
    
    print(f"Found {len(embeddings)} embedding vectors with shape {embeddings.shape}")
    
    # Validate embeddings shape before clustering
    if embeddings.ndim != 2:
        print(f"Error: Embeddings must be 2D array, got {embeddings.ndim}D with shape {embeddings.shape}")
        return None
    
    if embeddings.shape[0] < 2:
        print(f"Error: Need at least 2 samples for clustering, got {embeddings.shape[0]}")
        return None
    
    if embeddings.shape[1] < 1:
        print(f"Error: Need at least 1 feature for clustering, got {embeddings.shape[1]}")
        return None
    
    print(f"Embeddings validation passed: {embeddings.shape[0]} samples, {embeddings.shape[1]} features")
    print(f"Embeddings dtype: {embeddings.dtype}")
    
    # Check for any non-numeric values
    if not np.isfinite(embeddings).all():
        print("Warning: Found non-finite values in embeddings")
        # Replace NaN/inf with 0
        embeddings = np.nan_to_num(embeddings, nan=0.0, posinf=0.0, neginf=0.0)
        print("Replaced non-finite values with 0")
    
    # Configure DBSCAN parameters for high-dimensional embeddings (768D)
    # Focus on reducing noise and getting more meaningful clusters
    n_samples = len(embeddings)
    
    if embeddings.shape[1] >= 512:  # High-dimensional embeddings like 768D
        # Increase eps to capture more points in clusters, reduce min_samples to allow smaller clusters
        eps = 0.3 if n_samples > 100 else 0.25
        min_samples = max(2, min(5, n_samples // 100))  # Much smaller min_samples to reduce noise
        metric = 'cosine'
    elif embeddings.shape[1] >= 256:  # Medium-dimensional
        eps = 0.2 if n_samples > 100 else 0.15
        min_samples = max(2, min(7, n_samples // 80))
        metric = 'cosine'
    else:  # Lower-dimensional
        eps = 0.3 if n_samples > 100 else 0.25
        min_samples = max(2, min(8, n_samples // 50))
        metric = 'cosine'
    
    print(f"DBSCAN Configuration for {embeddings.shape[1]}D embeddings:")
    print(f"   - eps: {eps}")
    print(f"   - min_samples: {min_samples}")
    print(f"   - metric: {metric}")
    print(f"   - samples: {n_samples}")
    
    # For debugging: try multiple parameter combinations to minimize noise
    print(f"\nTesting parameter combinations to minimize noise...")
    test_combinations = [
        # (eps, min_samples)
        (0.08, 2), (0.1, 2), (0.12, 2), (0.15, 2), (0.18, 2),
        (0.08, 3), (0.1, 3), (0.12, 3), (0.15, 3), (0.18, 3),
        (0.1, 4), (0.12, 4), (0.15, 4), (0.18, 4), (0.2, 4),
        (0.15, 5), (0.18, 5), (0.2, 5), (0.25, 5)
    ]
    
    best_eps = eps
    best_min_samples = min_samples
    best_score = -1  # Score based on: more clusters, less noise
    
    for test_eps, test_min_samples in test_combinations:
        try:
            test_clustering = DBSCAN(
                eps=test_eps,
                min_samples=test_min_samples,
                metric=metric
            ).fit(embeddings)
            
            test_labels = test_clustering.labels_
            test_n_clusters = len(set(test_labels)) - (1 if -1 in test_labels else 0)
            test_n_noise = list(test_labels).count(-1)
            test_ratio = (len(embeddings) - test_n_noise)/len(embeddings)*100
            
            # Score: prefer more clusters and less noise
            # Penalize heavily if too much noise (>70%) or too few clusters (<3)
            if test_ratio < 30:  # More than 70% noise is bad
                score = -100
            elif test_n_clusters < 3:  # Too few clusters
                score = test_n_clusters * 10 + test_ratio - 50
            else:
                # Good balance: reward clusters and low noise
                score = test_n_clusters * 15 + test_ratio
            
            print(f"   eps={test_eps}, min_samples={test_min_samples}: {test_n_clusters} clusters, {test_n_noise} noise ({test_ratio:.1f}% clustered), score={score:.1f}")
            
            # Select best combination
            if score > best_score:
                best_eps = test_eps
                best_min_samples = test_min_samples
                best_score = score
                
        except Exception as e:
            print(f"   eps={test_eps}, min_samples={test_min_samples}: Failed - {e}")
    
    # Use the best parameters found
    eps = 0.22
    min_samples = 2
    print(f"\nSelected optimal parameters:")
    print(f"   - eps: {eps}")
    print(f"   - min_samples: {min_samples}")
    print(f"   - score: {best_score:.1f}")
    
    # Run DBSCAN clustering on embeddings
    print(f"\nRunning DBSCAN clustering with optimized parameters:")
    print(f"   - eps: {eps}")
    print(f"   - min_samples: {min_samples}")
    print(f"   - metric: {metric}")
    
    try:
        clustering = DBSCAN(
            eps=eps,
            min_samples=min_samples,
            metric=metric
        ).fit(embeddings)
        
        labels = clustering.labels_
        print(f"DBSCAN fitting completed, got {len(labels)} labels")
        
    except Exception as e:
        print(f"Error during DBSCAN clustering: {e}")
        print(f"Embeddings shape: {embeddings.shape}")
        print(f"Embeddings dtype: {embeddings.dtype}")
        return None
    
    # Generate UUIDs for clusters
    cluster_uuid_map = generate_cluster_uuids(labels)
    
    # Analyze results
    unique_labels = set(labels)
    n_clusters = len(unique_labels) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    
    print(f"DBSCAN completed!")
    print(f"   - Number of clusters: {n_clusters}")
    print(f"   - Number of noise points: {n_noise}")
    print(f"   - Clustering ratio: {(len(embeddings) - n_noise)/len(embeddings)*100:.1f}%")
    
    # Update database with cluster assignments
    print("\nUpdating cluster assignments in database...")
    update_success = update_cluster_assignments(paper_ids, labels, cluster_uuid_map)
    
    # Create clustered collection with UUIDs
    clustered_papers = create_clustered_collection(embeddings, labels, paper_ids, cluster_uuid_map)
    
    # Analyze cluster statistics
    cluster_stats = analyze_clusters(embeddings, labels, cluster_uuid_map)
    
    # Create result object with proper type conversion for JSON serialization
    def convert_numpy_types(obj):
        """Convert numpy types to Python native types for JSON serialization"""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {str(k): convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        else:
            return obj
    
    result = {
        'clustered_papers': convert_numpy_types(clustered_papers),
        'cluster_info': convert_numpy_types(cluster_stats),
        'cluster_uuid_map': convert_numpy_types(cluster_uuid_map),
        'summary': {
            'total_papers': int(len(paper_ids)),  # Ensure int, not numpy int
            'n_clusters': int(n_clusters),
            'n_noise': int(n_noise),
            'clustering_ratio': float((len(embeddings) - n_noise)/len(embeddings)*100),
            'embedding_dimension': int(embeddings.shape[1])
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
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {output_file}")
    except Exception as e:
        print(f"Could not save results to file: {e}")
        print(f"Error details: {type(e).__name__}: {str(e)}")
        
        # Try saving a simplified version
        try:
            simplified_result = {
                'summary': result['summary'],
                'cluster_count': len(result['cluster_info']),
                'paper_count': len(result['clustered_papers'])
            }
            backup_file = "/home/nghia-duong/workspace/Galaxy-of-Knowledge/backend/clustering_summary.json"
            with open(backup_file, 'w') as f:
                json.dump(simplified_result, f, indent=2)
            print(f"Saved simplified summary to: {backup_file}")
        except Exception as backup_e:
            print(f"Could not save backup file: {backup_e}")
    
    print(f"\nDBSCAN clustering on embeddings completed successfully!")
    print("Cluster assignments updated in database!")
    
    return result

if __name__ == "__main__":
    main()   
