#!/usr/bin/env python3
"""
FIRST CHOICE CLUSTERING: K-Means + L2 Normalization
Optimized specifically for Galaxy of Knowledge research paper embeddings
"""

import sys
import os
import subprocess

def run_kmeans_clustering():
    """Run K-Means clustering with L2 normalization - FIRST CHOICE"""
    
    print("🎯 GALAXY OF KNOWLEDGE - FIRST CHOICE CLUSTERING")
    print("="*60)
    print("🥇 ALGORITHM: K-Means")
    print("🔧 PREPROCESSING: L2 Normalization") 
    print("📊 OPTIMIZED FOR: Research Paper Embeddings")
    print("="*60)
    
    print("\n🔍 WHY K-MEANS + NORMALIZE IS BEST:")
    print("   ✅ SPEED: Fastest for large datasets")
    print("   ✅ CLEAR CLUSTERS: Non-overlapping topic separation")
    print("   ✅ VISUALIZATION: Perfect for 3D treemap display")
    print("   ✅ DETERMINISTIC: Consistent results across runs")
    print("   ✅ SEMANTIC: L2 norm preserves cosine similarity")
    print("   ✅ INTERPRETABLE: Each paper belongs to exactly 1 topic")
    
    print("\n🚀 STARTING K-MEANS CLUSTERING...")
    print("-" * 40)
    
    # Path to clustering script
    clustering_script = "/home/nghia-duong/workspace/Galaxy-of-Knowledge/backend/database/handle_3D/advanced_clustering.py"
    
    # Command to run K-Means with normalization
    cmd = [
        "python", clustering_script,
        "--algorithm", "kmeans", 
        "--preprocessing", "normalize"
    ]
    
    print(f"📋 COMMAND: {' '.join(cmd)}")
    print()
    
    try:
        # Run the clustering
        result = subprocess.run(cmd, 
                              capture_output=False,  # Show real-time output
                              text=True, 
                              timeout=600,  # 10 minutes timeout
                              cwd="/home/nghia-duong/workspace/Galaxy-of-Knowledge/backend")
        
        if result.returncode == 0:
            print("\n" + "="*60)
            print("🎉 K-MEANS CLUSTERING COMPLETED SUCCESSFULLY!")
            print("="*60)
            
            # Check for results file
            results_file = "/home/nghia-duong/workspace/Galaxy-of-Knowledge/backend/advanced_clustering_results.json"
            if os.path.exists(results_file):
                print("✅ Results saved to: advanced_clustering_results.json")
                
                # Show quick summary
                try:
                    import json
                    with open(results_file, 'r') as f:
                        results = json.load(f)
                    
                    summary = results.get('summary', {})
                    metrics = results.get('metrics', {})
                    
                    print(f"\n📊 CLUSTERING SUMMARY:")
                    print(f"   📄 Total papers: {summary.get('total_papers', 'N/A')}")
                    print(f"   🎯 Clusters found: {summary.get('n_clusters', 'N/A')}")
                    print(f"   📈 Silhouette score: {metrics.get('silhouette_score', 'N/A'):.3f}")
                    print(f"   🔧 Algorithm used: {results.get('algorithm_used', 'N/A')}")
                    print(f"   ⚙️  Preprocessing: {results.get('preprocessing', 'N/A')}")
                    
                except Exception as e:
                    print(f"   ⚠️  Could not parse results: {e}")
            
            print(f"\n🎯 NEXT STEPS:")
            print(f"   1️⃣  Generate AI topics: python generate_cluster_topics.py") 
            print(f"   2️⃣  Test saved topics: python test_saved_topics.py")
            print(f"   3️⃣  Start API server: python main.py")
            print(f"   4️⃣  View treemap data: GET /api/v1/stats/treemap")
            
            return True
            
        else:
            print(f"\n❌ K-MEANS CLUSTERING FAILED!")
            print(f"   Return code: {result.returncode}")
            if hasattr(result, 'stderr') and result.stderr:
                print(f"   Error: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\n⏰ CLUSTERING TIMED OUT (10 minutes)")
        print(f"   Your dataset might be very large")
        print(f"   Try with PCA preprocessing: --preprocessing pca")
        return False
        
    except Exception as e:
        print(f"\n💥 UNEXPECTED ERROR: {e}")
        return False

def check_prerequisites():
    """Check if all prerequisites are met"""
    
    print("🔍 CHECKING PREREQUISITES...")
    
    # Check if clustering script exists
    clustering_script = "/home/nghia-duong/workspace/Galaxy-of-Knowledge/backend/database/handle_3D/advanced_clustering.py"
    if not os.path.exists(clustering_script):
        print(f"❌ Clustering script not found: {clustering_script}")
        return False
    else:
        print(f"✅ Clustering script found")
    
    # Check environment file
    env_file = "/home/nghia-duong/workspace/Galaxy-of-Knowledge/backend/.env"
    if not os.path.exists(env_file):
        print(f"⚠️  Environment file not found: {env_file}")
        print(f"   Make sure your database credentials are configured")
    else:
        print(f"✅ Environment file found")
    
    # Check required Python packages
    required_packages = [
        'sklearn', 'numpy', 'psycopg2', 'hdbscan', 'python-dotenv'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} missing")
    
    if missing_packages:
        print(f"\n📦 INSTALL MISSING PACKAGES:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    print(f"✅ All prerequisites met!")
    return True

def main():
    """Main function"""
    
    print("🎯 GALAXY OF KNOWLEDGE - K-MEANS CLUSTERING")
    print("="*60)
    print("🥇 RUNNING FIRST CHOICE ALGORITHM")
    print("="*60)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please fix issues above.")
        return
    
    print()
    
    # Ask for confirmation
    response = input("🚀 Ready to run K-Means clustering? (y/n): ")
    
    if response.lower() in ['y', 'yes']:
        success = run_kmeans_clustering()
        
        if success:
            print(f"\n🎊 CLUSTERING PIPELINE READY!")
            print(f"   Your research papers are now clustered into topics")
            print(f"   Use the next steps above to generate AI topics and start the API")
        else:
            print(f"\n🔧 TROUBLESHOOTING TIPS:")
            print(f"   1. Check database connection in .env file")
            print(f"   2. Ensure you have papers with embeddings in database")
            print(f"   3. Try with smaller dataset first")
            print(f"   4. Check Python packages are installed")
            
    else:
        print(f"\n👍 Manual command to run K-Means clustering:")
        print(f"   cd /home/nghia-duong/workspace/Galaxy-of-Knowledge/backend")
        print(f"   python database/handle_3D/advanced_clustering.py --algorithm kmeans --preprocessing normalize")

if __name__ == "__main__":
    main()
