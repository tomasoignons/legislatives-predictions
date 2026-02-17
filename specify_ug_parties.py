#!/usr/bin/env python3
"""
Script to replace "UG" coalition labels with specific party affiliations
based on candidate information from the HTML file.

This script processes:
1. resultats_circonscription_tour_1.xlsx -> resultats_circonscription_tour_1_ug_specified.xlsx
2. candidatures_tour_2.xlsx -> candidatures_tour_2_ug_specified.xlsx
"""

import pandas as pd
import re
from pathlib import Path

# Mapping from HTML text to standardized party codes
PARTY_MAPPING = {
    "PS-PP": "PS",
    "Les Écologistes": "EELV",
    "FI": "FI",
    "PCF": "PCF",
    "G.s": "G.S",
    "Ouverture": "DVG",
    "REV": "REV",
    "Génération écologie": "ECO",
    "Euskal Herria Bai": "REG",
    "Picardie Debout": "DVG",
    "NPA": "EXG",
}


def parse_html_candidate_list(html_path):
    """
    Parse the HTML file to extract candidate information.
    
    Returns a dictionary mapping (dept_code, circonscription_num) -> (candidate_name, party)
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    candidates = {}
    current_dept_code = None
    
    # Split by paragraphs
    paragraphs = re.findall(r'<p>(.*?)</p>', content, re.DOTALL)
    
    for para in paragraphs:
        # Check if this is a department header (e.g., "AIN (01)" or "AISNE (02)")
        dept_match = re.search(r'<strong>([^<]+)</strong>\s*\((\d{2,3}[AB]?)\)', para)
        if dept_match:
            current_dept_code = dept_match.group(2)
            continue
        
        # Check if this is a candidate line
        # Pattern: "1ère circonscription : Name (PARTY)"
        candidate_match = re.search(
            r'(\d+)(?:ère|e|re)\s+circonscription\s*:\s*([^(]+)\(([^)]+)\)',
            para
        )
        
        if candidate_match and current_dept_code:
            circonscription_num = candidate_match.group(1)
            candidate_name = candidate_match.group(2).strip()
            party_text = candidate_match.group(3).strip()
            
            # Map to standardized party code
            party_code = PARTY_MAPPING.get(party_text, party_text)
            
            # Create the circonscription code (dept + circonscription num, zero-padded to 4 digits)
            # Format: dept (2-3 digits) + circonscription (1-2 digits), total 4 digits
            if len(current_dept_code) == 2:
                circonscription_code = f"{current_dept_code}{int(circonscription_num):02d}"
            else:  # 2A, 2B format
                circonscription_code = f"{current_dept_code}{int(circonscription_num):01d}"
            
            # Normalize candidate name (lowercase, remove extra spaces)
            candidate_name_normalized = ' '.join(candidate_name.lower().split())
            
            candidates[circonscription_code] = {
                'name': candidate_name_normalized,
                'party': party_code,
                'original_party_text': party_text
            }
    
    return candidates


def normalize_name(name):
    """Normalize a name for comparison: lowercase, remove extra spaces."""
    if pd.isna(name):
        return ""
    return ' '.join(str(name).lower().split())


def find_candidate_party(nom, prenom, circonscription_code, candidates_dict):
    """
    Find the party affiliation for a candidate based on their name and circonscription.
    
    Returns the party code or None if not found.
    """
    if circonscription_code not in candidates_dict:
        return None
    
    candidate_info = candidates_dict[circonscription_code]
    candidate_full_name = candidate_info['name']
    
    # Normalize the names from the dataset
    nom_normalized = normalize_name(nom)
    prenom_normalized = normalize_name(prenom)
    full_name = f"{prenom_normalized} {nom_normalized}".strip()
    
    # Check if the names match (either order)
    if (prenom_normalized in candidate_full_name and nom_normalized in candidate_full_name) or \
       (candidate_full_name in full_name) or \
       (full_name in candidate_full_name):
        return candidate_info['party']
    
    return None


def process_resultats_circonscription_tour_1(input_path, output_path, candidates_dict):
    """
    Process the resultats_circonscription_tour_1.xlsx file.
    Replace "UG" nuances with specific party codes where applicable.
    """
    print(f"Loading {input_path}...")
    df = pd.read_excel(input_path)
    
    print(f"Original shape: {df.shape}")
    
    # Track statistics
    total_ug = 0
    replaced = 0
    not_found = 0
    
    # Iterate through all candidate columns
    # Based on the notebook, there are columns like "Nuance candidat 1", "Nom 1", "Prénom 1", etc.
    max_candidates = 15  # Adjust based on your data
    
    for i in range(1, max_candidates + 1):
        nuance_col = f"Nuance candidat {i}"
        nom_col = f"Nom {i}"
        prenom_col = f"Prénom {i}"
        
        if nuance_col not in df.columns:
            continue
        
        # Find rows where this candidate has "UG" nuance
        ug_mask = df[nuance_col] == "UG"
        total_ug += ug_mask.sum()
        
        for idx in df[ug_mask].index:
            row = df.loc[idx]
            
            # Get the circonscription code
            circonscription_code = str(row.get("Code circonscription législative", "")).zfill(4)
            
            # Get candidate names
            nom = row.get(nom_col)
            prenom = row.get(prenom_col)
            
            # Find the party
            party = find_candidate_party(nom, prenom, circonscription_code, candidates_dict)
            
            if party:
                df.loc[idx, nuance_col] = party
                replaced += 1
            else:
                not_found += 1
    
    print(f"\nStatistics for resultats_circonscription_tour_1:")
    print(f"  Total UG candidates found: {total_ug}")
    print(f"  Successfully replaced: {replaced}")
    print(f"  Not found in candidate list: {not_found}")
    
    # Save the result
    print(f"\nSaving to {output_path}...")
    df.to_excel(output_path, index=False)
    print("Done!")
    
    return df


def process_candidatures_tour_2(input_path, output_path, candidates_dict):
    """
    Process the candidatures_tour_2.xlsx file.
    Replace "UG" nuances with specific party codes where applicable.
    """
    print(f"\nLoading {input_path}...")
    df = pd.read_excel(input_path)
    
    print(f"Original shape: {df.shape}")
    
    # Track statistics
    total_ug = 0
    replaced = 0
    not_found = 0
    
    # Check for UG in the nuance column (adjust column name as needed)
    nuance_col = "Code nuance"  # Adjust if the column has a different name
    
    if nuance_col in df.columns:
        ug_mask = df[nuance_col] == "UG"
        total_ug = ug_mask.sum()
        
        for idx in df[ug_mask].index:
            row = df.loc[idx]
            
            # Get the circonscription code
            circonscription_code = str(row.get("Code circonscription", "")).zfill(4)
            
            # Get candidate names
            nom = row.get("Nom")
            prenom = row.get("Prénom")
            
            # Find the party
            party = find_candidate_party(nom, prenom, circonscription_code, candidates_dict)
            
            if party:
                df.loc[idx, nuance_col] = party
                replaced += 1
            else:
                not_found += 1
    else:
        print(f"Warning: Column '{nuance_col}' not found in the dataset.")
        print(f"Available columns: {list(df.columns)}")
    
    print(f"\nStatistics for candidatures_tour_2:")
    print(f"  Total UG candidates found: {total_ug}")
    print(f"  Successfully replaced: {replaced}")
    print(f"  Not found in candidate list: {not_found}")
    
    # Save the result
    print(f"\nSaving to {output_path}...")
    df.to_excel(output_path, index=False)
    print("Done!")
    
    return df


def process_resultats_circonscription_tour_2(input_path, output_path, candidates_dict):
    """
    Process the resultats_circonscription_tour_2.xlsx file.
    Replace "UG" nuances with specific party codes where applicable.
    """
    print(f"Loading {input_path}...")
    df = pd.read_excel(input_path)
    
    print(f"Original shape: {df.shape}")
    
    # Track statistics
    total_ug = 0
    replaced = 0
    not_found = 0
    
    # Iterate through all candidate columns
    # Based on the notebook, there are columns like "Nuance candidat 1", "Nom 1", "Prénom 1", etc.
    max_candidates = 6  # Tour 2 typically has fewer candidates
    
    for i in range(1, max_candidates + 1):
        nuance_col = f"Nuance candidat {i}"
        nom_col = f"Nom {i}"
        prenom_col = f"Prénom {i}"
        
        if nuance_col not in df.columns:
            continue
        
        # Find rows where this candidate has "UG" nuance
        ug_mask = df[nuance_col] == "UG"
        total_ug += ug_mask.sum()
        
        for idx in df[ug_mask].index:
            row = df.loc[idx]
            
            # Get the circonscription code
            circonscription_code = str(row.get("Code circonscription législative", "")).zfill(4)
            
            # Get candidate names
            nom = row.get(nom_col)
            prenom = row.get(prenom_col)
            
            # Find the party
            party = find_candidate_party(nom, prenom, circonscription_code, candidates_dict)
            
            if party:
                df.loc[idx, nuance_col] = party
                replaced += 1
            else:
                not_found += 1
    
    print(f"\nStatistics for resultats_circonscription_tour_2:")
    print(f"  Total UG candidates found: {total_ug}")
    print(f"  Successfully replaced: {replaced}")
    print(f"  Not found in candidate list: {not_found}")
    
    # Save the result
    print(f"\nSaving to {output_path}...")
    df.to_excel(output_path, index=False)
    print("Done!")
    
    return df


def main():
    """Main function to process all datasets."""
    
    # Define paths
    data_dir = Path("./data")
    html_file = data_dir / "liste_candidates_humanite.html"
    
    resultats_tour_1_input = data_dir / "resultats_circonscription_tour_1.xlsx"
    resultats_tour_1_output = data_dir / "resultats_circonscription_tour_1_ug_specified.xlsx"
    
    resultats_tour_2_input = data_dir / "resultats_circonscription_tour_2.xlsx"
    resultats_tour_2_output = data_dir / "resultats_circonscription_tour_2_ug_specified.xlsx"
    
    candidatures_tour_2_input = data_dir / "candidatures_tour_2.xlsx"
    candidatures_tour_2_output = data_dir / "candidatures_tour_2_ug_specified.xlsx"
    
    # Check if files exist
    if not html_file.exists():
        print(f"Error: HTML file not found at {html_file}")
        return
    
    print("=" * 70)
    print("UG Party Specification Script")
    print("=" * 70)
    
    # Parse the HTML candidate list
    print("\nParsing candidate list from HTML...")
    candidates_dict = parse_html_candidate_list(html_file)
    print(f"Found {len(candidates_dict)} candidates in the HTML file")
    
    # Show a few examples
    print("\nExample entries:")
    for i, (code, info) in enumerate(list(candidates_dict.items())[:5]):
        print(f"  {code}: {info['name']} -> {info['party']}")
    
    # Process resultats_circonscription_tour_1
    if resultats_tour_1_input.exists():
        print("\n" + "=" * 70)
        print("Processing resultats_circonscription_tour_1.xlsx")
        print("=" * 70)
        process_resultats_circonscription_tour_1(
            resultats_tour_1_input,
            resultats_tour_1_output,
            candidates_dict
        )
    else:
        print(f"\nWarning: {resultats_tour_1_input} not found, skipping...")
    
    # Process resultats_circonscription_tour_2
    if resultats_tour_2_input.exists():
        print("\n" + "=" * 70)
        print("Processing resultats_circonscription_tour_2.xlsx")
        print("=" * 70)
        process_resultats_circonscription_tour_2(
            resultats_tour_2_input,
            resultats_tour_2_output,
            candidates_dict
        )
    else:
        print(f"\nWarning: {resultats_tour_2_input} not found, skipping...")
    
    # Process candidatures_tour_2
    if candidatures_tour_2_input.exists():
        print("\n" + "=" * 70)
        print("Processing candidatures_tour_2.xlsx")
        print("=" * 70)
        process_candidatures_tour_2(
            candidatures_tour_2_input,
            candidatures_tour_2_output,
            candidates_dict
        )
    else:
        print(f"\nWarning: {candidatures_tour_2_input} not found, skipping...")
    
    print("\n" + "=" * 70)
    print("All processing complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
