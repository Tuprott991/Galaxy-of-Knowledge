#!/usr/bin/env python3
"""
Test script for html_context insertion functionality
"""

import sys
import os

# Add the parent directory to the path so we can import from database modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.html_context import HTMLContextDatabase, update_specific_papers_html_context

def test_html_context_insertion():
    """Test the html_context insertion with a specific paper"""
    
    print("🧪 Testing HTML Context Insertion")
    print("=" * 50)
    
    # Test with PMC2824534 as we know this file exists
    test_paper_id = "PMC2824534"
    folder_path = "d:/Github Repos/Galaxy-of-Knowledge/backend/database/PMC_txt"
    
    # Initialize database connection
    db = HTMLContextDatabase()
    
    try:
        # Check if the paper exists in database
        print(f"1. Checking if paper {test_paper_id} exists in database...")
        paper_exists = db.check_paper_exists(test_paper_id)
        print(f"   Result: {'✅ Found' if paper_exists else '❌ Not found'}")
        
        if not paper_exists:
            print(f"   ⚠️  Paper {test_paper_id} not found in database. Cannot test.")
            return
        
        # Check if the file exists
        test_file_path = os.path.join(folder_path, f"{test_paper_id}.txt")
        print(f"2. Checking if file {test_paper_id}.txt exists...")
        file_exists = os.path.exists(test_file_path)
        print(f"   Result: {'✅ Found' if file_exists else '❌ Not found'}")
        
        if not file_exists:
            print(f"   ⚠️  File {test_file_path} not found. Cannot test.")
            return
        
        # Test the update function
        print(f"3. Testing HTML context update for {test_paper_id}...")
        result = update_specific_papers_html_context(folder_path, [test_paper_id])
        successful_updates, failed_updates, skipped_files = result
        
        print(f"   Results:")
        print(f"   - Successful updates: {successful_updates}")
        print(f"   - Failed updates: {failed_updates}")
        print(f"   - Skipped files: {skipped_files}")
        
        if successful_updates > 0:
            print(f"   ✅ Test passed! HTML context updated successfully.")
        else:
            print(f"   ⚠️  Test completed but no updates were made (might already exist).")
            
    except Exception as e:
        print(f"   ❌ Test failed with error: {e}")
    
    finally:
        db.close()
        
    print("\n🏁 Test completed")

def test_get_papers_without_html_context():
    """Test getting papers without html_context"""
    
    print("\n🔍 Testing Get Papers Without HTML Context")
    print("=" * 50)
    
    db = HTMLContextDatabase()
    
    try:
        papers_without_context = db.get_papers_without_html_context()
        print(f"Found {len(papers_without_context)} papers without html_context")
        
        if papers_without_context:
            print("First 5 papers without html_context:")
            for i, paper_id in enumerate(papers_without_context[:5], 1):
                print(f"   {i}. {paper_id}")
                
            if len(papers_without_context) > 5:
                print(f"   ... and {len(papers_without_context) - 5} more")
        else:
            print("✅ All papers already have html_context!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        db.close()

if __name__ == "__main__":
    test_html_context_insertion()
    test_get_papers_without_html_context()