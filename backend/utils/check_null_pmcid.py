#!/usr/bin/env python3
"""
Script to list filenames that have null/empty PMCID or duplicate PMCID
"""
import os
import json
from collections import defaultdict

def check_pmcid_issues(folder_path: str):
    """Check and print files with null/empty PMCID and duplicate PMCID"""
    
    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return
    
    json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
    print(f"Checking {len(json_files)} JSON files...\n")
    
    null_files = []
    pmcid_to_files = defaultdict(list)  # Track which files have which PMCID
    
    for filename in json_files:
        file_path = os.path.join(folder_path, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            pmcid = data.get("PMCID", "")
            
            # Check if PMCID is null/empty
            if not pmcid or pmcid.strip() == "":
                null_files.append(filename)
            else:
                # Track PMCID for duplicate detection
                pmcid_to_files[pmcid.strip()].append(filename)
                
        except Exception as e:
            print(f"ERROR reading {filename}: {e}")
    
    # Find duplicates
    duplicate_groups = {pmcid: files for pmcid, files in pmcid_to_files.items() if len(files) > 1}
    
    # Print results
    print("=" * 60)
    print("FILES WITH NULL/EMPTY PMCID:")
    print("=" * 60)
    if null_files:
        for filename in null_files:
            print(filename)
        print(f"\nTotal: {len(null_files)} files")
    else:
        print("No files with null PMCID found")
    
    print("\n" + "=" * 60)
    print("FILES WITH DUPLICATE PMCID:")
    print("=" * 60)
    if duplicate_groups:
        for pmcid, files in duplicate_groups.items():
            print(f"\nPMCID: {pmcid}")
            for filename in files:
                print(f"  - {filename}")
        
        total_duplicate_files = sum(len(files) for files in duplicate_groups.values())
        print(f"\nTotal duplicate groups: {len(duplicate_groups)}")
        print(f"Total files in duplicates: {total_duplicate_files}")
    else:
        print("No duplicate PMCID found")
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("=" * 60)
    print(f"Total files: {len(json_files)}")
    print(f"Files with null PMCID: {len(null_files)}")
    print(f"Files with duplicate PMCID: {sum(len(files) for files in duplicate_groups.values())}")
    print(f"Unique valid PMCID: {len([pmcid for pmcid, files in pmcid_to_files.items() if len(files) == 1])}")

def main():
    folder_path = "/home/nghia-duong/Downloads/PMC_articles_json (2)/PMC_articles_json"
    check_pmcid_issues(folder_path)

if __name__ == "__main__":
    main()
