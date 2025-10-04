#!/usr/bin/env python3
"""
K-Means Clustering for High-Dimensional Embeddings
Optimized specifically for Galaxy of Knowledge research paper embeddings
"""

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, calinski_harabasz_score
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
            
            # Ensure proper shape for K-Means
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

def preprocess_embeddings(embeddings, method='normalize'):
    """Preprocess embeddings for better clustering"""
    print(f"Preprocessing embeddings with method: {method}")
    
    # Remove any infinite/NaN values
    embeddings = np.nan_to_num(embeddings, nan=0.0, posinf=0.0, neginf=0.0)
    
    if method == 'normalize':
        # L2 normalization (good for cosine similarity)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        embeddings = embeddings / norms
        print("Applied L2 normalization for cosine similarity")
    
    return embeddings

def find_optimal_k(embeddings, max_k=40):
    """Find optimal number of clusters for K-Means focusing on cluster quality"""
    print("Finding optimal K for K-Means (optimized for quality over quantity)...")
    
    # More conservative approach: focus on quality clusters
    max_k = min(max_k, len(embeddings) // 4)  # At least 4 points per cluster (increased from 2)
    if max_k < 8:
        return 10  # Conservative default
    
    # Start from reasonable minimum
    min_k = max(6, min(12, len(embeddings) // 25))  # Start from 6-12 clusters
    k_range = range(min_k, max_k + 1)
    
    best_k = min_k
    best_score = -1
    
    for k in k_range:
        try:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=15)
            labels = kmeans.fit_predict(embeddings)
            
            # Calculate silhouette score
            if len(set(labels)) > 1:  # Need more than 1 cluster
                sil_score = silhouette_score(embeddings, labels)
                
                # Combined score: favor more clusters while maintaining quality
                unique_labels, counts = np.unique(labels, return_counts=True)
                balance_score = 1.0 - np.std(counts) / np.mean(counts)  # Lower std = better balance
                
                # Reward MORE clusters aggressively (for granular topics)
                cluster_bonus = min(1.2, k / 20.0)  # Higher bonus for having more clusters up to 20+
                
                # Combined score with higher cluster preference
                combined_score = sil_score * 0.4 + balance_score * 0.2 + cluster_bonus * 0.4
                
                print(f"   K={k}: silhouette={sil_score:.3f}, balance={balance_score:.3f}, cluster_bonus={cluster_bonus:.3f}, combined={combined_score:.3f}")
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_k = k
                
        except Exception as e:
            print(f"   K={k}: Failed - {e}")
    
    print(f"Optimal K selected: {best_k} (score: {best_score:.3f})")
    return best_k

def generate_cluster_uuids(labels):
    """Generate UUIDs for each unique cluster"""
    unique_labels = set(labels)
    cluster_uuid_map = {}
    
    for cluster_id in unique_labels:
        # Generate unique UUID for each cluster
        cluster_uuid_map[cluster_id] = str(uuid.uuid4())
    
    return cluster_uuid_map

def create_clustered_collection(embeddings, labels, paper_ids, cluster_uuid_map):
    """Create collection with cluster UUIDs for frontend"""
    clustered_papers = []
    
    for i, (paper_id, label) in enumerate(zip(paper_ids, labels)):
        cluster_uuid = cluster_uuid_map[label]
        
        paper = {
            'paper_id': paper_id,
            'cluster_uuid': cluster_uuid,
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

def analyze_cluster_confidence(embeddings, labels, kmeans_model):
    """Analyze confidence of cluster assignments and identify potential 'noise' papers"""
    print("Analyzing cluster assignment confidence...")
    
    cluster_centers = kmeans_model.cluster_centers_
    confidences = []
    potential_noise = []
    
    for i, (embedding, label) in enumerate(zip(embeddings, labels)):
        # Calculate distances to all cluster centers
        distances = [np.linalg.norm(embedding - center) for center in cluster_centers]
        
        # Distance to assigned cluster
        assigned_distance = distances[label]
        
        # Distance to closest alternative cluster
        distances_copy = distances.copy()
        distances_copy.pop(label)
        min_alternative_distance = min(distances_copy)
        
        # Confidence: ratio of alternative distance to assigned distance
        # Higher ratio = more confident assignment
        confidence = min_alternative_distance / assigned_distance if assigned_distance > 0 else 1.0
        confidences.append(confidence)
        
        # Mark as potential noise if confidence is low (close to multiple clusters)
        if confidence < 1.2:  # Very close to other clusters
            potential_noise.append(i)
    
    avg_confidence = np.mean(confidences)
    print(f"   - Average confidence: {avg_confidence:.3f}")
    print(f"   - Potential ambiguous papers: {len(potential_noise)} ({len(potential_noise)/len(labels)*100:.1f}%)")
    
    return confidences, potential_noise

def analyze_clusters(embeddings, labels, cluster_uuid_map, confidences=None, potential_noise=None):
    """Analyze cluster statistics with UUIDs and confidence info"""
    unique_labels = set(labels)
    cluster_stats = {}
    
    for cluster_id in unique_labels:
        cluster_mask = labels == cluster_id
        cluster_embeddings = embeddings[cluster_mask]
        cluster_uuid = cluster_uuid_map[cluster_id]
        
        # Calculate confidence stats for this cluster
        cluster_confidences = []
        cluster_ambiguous = 0
        
        if confidences is not None and potential_noise is not None:
            cluster_indices = np.where(cluster_mask)[0]
            for idx in cluster_indices:
                cluster_confidences.append(confidences[idx])
                if idx in potential_noise:
                    cluster_ambiguous += 1
        
        avg_confidence = np.mean(cluster_confidences) if cluster_confidences else 0.0
        
        cluster_stats[cluster_uuid] = {
            'cluster_uuid': cluster_uuid,
            'count': len(cluster_embeddings),
            'centroid_dimension': len(embeddings[0]),  # Embedding dimension
            'type': 'cluster',
            'avg_confidence': float(avg_confidence),
            'ambiguous_papers': cluster_ambiguous,
            'confidence_ratio': float(cluster_ambiguous / len(cluster_embeddings) * 100) if len(cluster_embeddings) > 0 else 0.0
        }
    
    return cluster_stats

def main():
    """Main function to run K-Means clustering on embeddings"""
    print("Starting K-Means Clustering on Embeddings")
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
    
    # Preprocess embeddings with L2 normalization
    embeddings = preprocess_embeddings(embeddings, method='normalize')
    
    # Find optimal number of clusters
    optimal_k = find_optimal_k(embeddings)
    
    print(f"\nRunning K-Means clustering:")
    print(f"   - n_clusters: {optimal_k}")
    print(f"   - random_state: 42")
    print(f"   - n_init: 30")
    print(f"   - max_iter: 1000")
    print(f"   - algorithm: lloyd")
    print(f"   - init: k-means++")
    print(f"   - Optimized for MORE CLUSTERS and better topic separation")
    
    try:
        # Run K-Means clustering with optimized parameters for more clusters
        kmeans = KMeans(
            n_clusters=optimal_k,
            random_state=42,
            n_init=30,  # More initializations for better cluster separation
            max_iter=1000,  # More iterations for convergence
            algorithm='lloyd',  # Classic algorithm for better results
            init='k-means++'  # Smart initialization
        )
        
        labels = kmeans.fit_predict(embeddings)
        print(f"K-Means fitting completed, got {len(labels)} labels")
        
        # Analyze cluster assignment confidence
        confidences, potential_noise = analyze_cluster_confidence(embeddings, labels, kmeans)
        
        # Calculate quality metrics
        silhouette_avg = silhouette_score(embeddings, labels)
        calinski_score = calinski_harabasz_score(embeddings, labels)
        
        print(f"K-Means Quality Metrics:")
        print(f"   - Silhouette Score: {silhouette_avg:.3f}")
        print(f"   - Calinski-Harabasz Score: {calinski_score:.3f}")
        
    except Exception as e:
        print(f"Error during K-Means clustering: {e}")
        print(f"Embeddings shape: {embeddings.shape}")
        print(f"Embeddings dtype: {embeddings.dtype}")
        return None
    
    # Generate UUIDs for clusters
    cluster_uuid_map = generate_cluster_uuids(labels)
    
    # Analyze results
    unique_labels = set(labels)
    n_clusters = len(unique_labels)
    
    print(f"K-Means completed!")
    print(f"   - Number of clusters: {n_clusters}")
    print(f"   - All papers clustered (no noise in K-Means)")
    print(f"   - Clustering ratio: 100.0%")
    print(f"   - Ambiguous papers: {len(potential_noise)} ({len(potential_noise)/len(labels)*100:.1f}%)")
    
    # Update database with cluster assignments
    print("\nUpdating cluster assignments in database...")
    update_success = update_cluster_assignments(paper_ids, labels, cluster_uuid_map)
    
    # Create clustered collection with UUIDs
    clustered_papers = create_clustered_collection(embeddings, labels, paper_ids, cluster_uuid_map)
    
    # Analyze cluster statistics with confidence info
    cluster_stats = analyze_clusters(embeddings, labels, cluster_uuid_map, confidences, potential_noise)
    
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
        'metrics': {
            'algorithm': 'kmeans',
            'n_clusters': int(optimal_k),
            'silhouette_score': float(silhouette_avg),
            'calinski_score': float(calinski_score)
        },
        'summary': {
            'total_papers': int(len(paper_ids)),
            'n_clusters': int(n_clusters),
            'n_noise': 0,  # K-Means doesn't produce noise
            'n_ambiguous': len(potential_noise),  # Papers close to multiple clusters
            'clustering_ratio': 100.0,  # All points are clustered
            'ambiguous_ratio': float(len(potential_noise)/len(labels)*100),
            'avg_confidence': float(np.mean(confidences)),
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
        confidence_info = f" (avg_conf: {stats['avg_confidence']:.2f}, ambiguous: {stats['ambiguous_papers']})"
        print(f"   Cluster {cluster_uuid[:8]}...: {stats['count']} papers{confidence_info}")
    
    # Save results to JSON file
    output_file = "/home/nghia-duong/workspace/Galaxy-of-Knowledge/backend/kmeans_clustering_results.json"
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
                'metrics': result['metrics'],
                'cluster_count': len(result['cluster_info']),
                'paper_count': len(result['clustered_papers'])
            }
            backup_file = "/home/nghia-duong/workspace/Galaxy-of-Knowledge/backend/kmeans_summary.json"
            with open(backup_file, 'w') as f:
                json.dump(simplified_result, f, indent=2)
            print(f"Saved simplified summary to: {backup_file}")
        except Exception as backup_e:
            print(f"Could not save backup file: {backup_e}")
    
    print(f"\nK-Means clustering on embeddings completed successfully!")
    print("Cluster assignments updated in database!")
    
    return result

if __name__ == "__main__":
    main()
