from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import sys
import os

# Add parent directory to path to import database modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connect import connect, close_connection

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

class PapersAPI:
    def __init__(self):
        self.conn = None
    
    def get_connection(self):
        """Get database connection"""
        if not self.conn:
            self.conn = connect()
        return self.conn
    
    def close_connection(self):
        """Close database connection"""
        if self.conn:
            close_connection(self.conn)
            self.conn = None

    def get_papers_visualization_data(self, limit=None):
        """
        Get papers data for 3D visualization
        Returns: List of objects with x, y, z, cluster, title
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Query to get visualization data
            query = """
                SELECT 
                    plot_visualize_x as x,
                    plot_visualize_y as y, 
                    plot_visualize_z as z,
                    cluster,
                    title,
                    paper_id
                FROM paper 
                WHERE plot_visualize_x IS NOT NULL 
                  AND plot_visualize_y IS NOT NULL 
                  AND plot_visualize_z IS NOT NULL
                  AND title IS NOT NULL
                ORDER BY id
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Convert to list of dictionaries
            papers_data = []
            for row in results:
                papers_data.append({
                    'x': float(row[0]) if row[0] is not None else 0.0,
                    'y': float(row[1]) if row[1] is not None else 0.0,
                    'z': float(row[2]) if row[2] is not None else 0.0,
                    'cluster': row[3] if row[3] else 'unclustered',
                    'title': row[4] if row[4] else 'No Title',
                    'paper_id': row[5] if row[5] else ''
                })
            
            cursor.close()
            logger.info(f"Retrieved {len(papers_data)} papers for visualization")
            
            return papers_data
            
        except Exception as e:
            logger.error(f"Error getting papers visualization data: {e}")
            raise

# Initialize API instance
api = PapersAPI()

@app.route('/api/v1/papers/visualization', methods=['GET'])
def get_papers_visualization():
    """
    API endpoint to get papers visualization data
    Query parameters:
        - limit: Optional limit for number of papers to return
    
    Returns:
        JSON response with papers data for 3D visualization
    """
    try:
        # Get query parameters
        limit = request.args.get('limit', type=int)
        
        # Get papers data
        papers_data = api.get_papers_visualization_data(limit=limit)
        
        # Return JSON response
        return jsonify({
            'success': True,
            'data': papers_data,
            'count': len(papers_data),
            'message': f'Successfully retrieved {len(papers_data)} papers'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in visualization API: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve papers visualization data'
        }), 500

@app.route('/api/v1/papers/stats', methods=['GET'])
def get_papers_stats():
    """
    API endpoint to get basic statistics about papers
    
    Returns:
        JSON response with statistics
    """
    try:
        conn = api.get_connection()
        cursor = conn.cursor()
        
        # Get basic statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_papers,
                COUNT(CASE WHEN plot_visualize_x IS NOT NULL THEN 1 END) as papers_with_coordinates,
                COUNT(CASE WHEN cluster IS NOT NULL THEN 1 END) as papers_with_clusters,
                COUNT(DISTINCT cluster) as unique_clusters,
                COUNT(CASE WHEN title IS NOT NULL THEN 1 END) as papers_with_titles
            FROM paper
        """
        
        cursor.execute(stats_query)
        stats = cursor.fetchone()
        
        # Get cluster distribution
        cluster_query = """
            SELECT 
                cluster,
                COUNT(*) as count
            FROM paper 
            WHERE cluster IS NOT NULL
            GROUP BY cluster
            ORDER BY count DESC
        """
        
        cursor.execute(cluster_query)
        cluster_distribution = cursor.fetchall()
        
        cursor.close()
        
        # Format response
        response_data = {
            'total_papers': stats[0],
            'papers_with_coordinates': stats[1],
            'papers_with_clusters': stats[2],
            'unique_clusters': stats[3],
            'papers_with_titles': stats[4],
            'cluster_distribution': [
                {'cluster': row[0], 'count': row[1]} 
                for row in cluster_distribution
            ]
        }
        
        return jsonify({
            'success': True,
            'data': response_data,
            'message': 'Successfully retrieved papers statistics'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in stats API: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve papers statistics'
        }), 500

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'Papers API is running',
        'version': '1.0.0'
    }), 200

# Cleanup on app teardown
@app.teardown_appcontext
def close_db(error):
    """Close database connection on app teardown"""
    api.close_connection()

if __name__ == '__main__':
    # Development server
    app.run(host='0.0.0.0', port=5000, debug=True)
