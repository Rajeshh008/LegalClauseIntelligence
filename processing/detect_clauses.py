import re
from typing import List, Dict, Tuple
import logging

def detect_clauses(text: str) -> List[str]:
    """
    Detect and extract individual clauses from contract text.
    
    Args:
        text (str): Full contract text
        
    Returns:
        List[str]: List of detected clauses
    """
    if not text or not text.strip():
        return []
    
    # Clean the text first
    cleaned_text = clean_text_for_clause_detection(text)
    
    # Try multiple detection methods
    clauses = []
    
    # Method 1: Numbered sections (1., 2., 1.1, etc.)
    numbered_clauses = detect_numbered_clauses(cleaned_text)
    if numbered_clauses and len(numbered_clauses) > 2:
        clauses = numbered_clauses
    
    # Method 2: Header-based detection if numbered detection fails
    if not clauses:
        header_clauses = detect_header_based_clauses(cleaned_text)
        if header_clauses and len(header_clauses) > 1:
            clauses = header_clauses
    
    # Method 3: Paragraph-based detection as fallback
    if not clauses:
        clauses = detect_paragraph_based_clauses(cleaned_text)
    
    # Filter out very short clauses (likely headers or artifacts)
    filtered_clauses = []
    for clause in clauses:
        if len(clause.strip()) > 50:  # Minimum clause length
            filtered_clauses.append(clause.strip())
    
    return filtered_clauses if filtered_clauses else [cleaned_text]

def clean_text_for_clause_detection(text: str) -> str:
    """
    Clean text to improve clause detection accuracy.
    
    Args:
        text (str): Raw text
        
    Returns:
        str: Cleaned text
    """
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    return text.strip()

def detect_numbered_clauses(text: str) -> List[str]:
    """
    Detect clauses based on numbered sections (1., 2., 1.1, etc.).
    
    Args:
        text (str): Contract text
        
    Returns:
        List[str]: List of detected clauses
    """
    # Pattern for numbered sections
    patterns = [
        r'^\s*(\d+\.\s)',  # 1. 2. 3.
        r'^\s*(\d+\.\d+\s)',  # 1.1 1.2 2.1
        r'^\s*(\(\d+\)\s)',  # (1) (2) (3)
        r'^\s*([A-Z]\.\s)',  # A. B. C.
        r'^\s*(Article\s+\d+)',  # Article 1, Article 2
        r'^\s*(Section\s+\d+)',  # Section 1, Section 2
    ]
    
    for pattern in patterns:
        matches = list(re.finditer(pattern, text, re.MULTILINE))
        if len(matches) >= 2:  # Need at least 2 sections
            clauses = []
            for i, match in enumerate(matches):
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                clause_text = text[start:end].strip()
                if clause_text:
                    clauses.append(clause_text)
            return clauses
    
    return []

def detect_header_based_clauses(text: str) -> List[str]:
    """
    Detect clauses based on common legal headers.
    
    Args:
        text (str): Contract text
        
    Returns:
        List[str]: List of detected clauses
    """
    # Common legal clause headers
    headers = [
        r'^\s*(TERMINATION|Termination)',
        r'^\s*(LIABILITY|Liability)',
        r'^\s*(CONFIDENTIALITY|Confidentiality)',
        r'^\s*(NON-DISCLOSURE|Non-Disclosure)',
        r'^\s*(PAYMENT|Payment)',
        r'^\s*(INTELLECTUAL PROPERTY|Intellectual Property)',
        r'^\s*(GOVERNING LAW|Governing Law)',
        r'^\s*(DISPUTE RESOLUTION|Dispute Resolution)',
        r'^\s*(FORCE MAJEURE|Force Majeure)',
        r'^\s*(INDEMNIFICATION|Indemnification)',
        r'^\s*(WARRANTIES|Warranties)',
        r'^\s*(LIMITATION OF LIABILITY|Limitation of Liability)',
        r'^\s*(ENTIRE AGREEMENT|Entire Agreement)',
        r'^\s*(AMENDMENT|Amendment)',
        r'^\s*(ASSIGNMENT|Assignment)',
        r'^\s*(SEVERABILITY|Severability)',
        r'^\s*(NOTICES|Notices)',
        r'^\s*(DEFINITIONS|Definitions)',
        r'^\s*(SCOPE OF WORK|Scope of Work)',
        r'^\s*(DELIVERABLES|Deliverables)',
        r'^\s*(TERM|Term)',
        r'^\s*(RENEWAL|Renewal)',
        r'^\s*(CANCELLATION|Cancellation)',
        r'^\s*(JURISDICTION|Jurisdiction)',
        r'^\s*(COMPLIANCE|Compliance)',
        r'^\s*(DATA PROTECTION|Data Protection)',
        r'^\s*(PRIVACY|Privacy)',
    ]
    
    # Combine all patterns
    combined_pattern = '|'.join(headers)
    
    matches = list(re.finditer(combined_pattern, text, re.MULTILINE | re.IGNORECASE))
    
    if len(matches) >= 2:
        clauses = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            clause_text = text[start:end].strip()
            if clause_text:
                clauses.append(clause_text)
        return clauses
    
    return []

def detect_paragraph_based_clauses(text: str) -> List[str]:
    """
    Fallback method: split text into paragraphs as clauses.
    
    Args:
        text (str): Contract text
        
    Returns:
        List[str]: List of paragraphs as clauses
    """
    # Split by double newlines (paragraph breaks)
    paragraphs = re.split(r'\n\s*\n', text)
    
    # Filter out very short paragraphs
    clauses = []
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if len(paragraph) > 100:  # Minimum paragraph length for legal clauses
            clauses.append(paragraph)
    
    return clauses

def identify_clause_boundaries(text: str) -> List[Tuple[int, int]]:
    """
    Identify start and end positions of clauses in text.
    
    Args:
        text (str): Contract text
        
    Returns:
        List[Tuple[int, int]]: List of (start, end) positions for each clause
    """
    boundaries = []
    
    # Use numbered section detection for boundaries
    pattern = r'^\s*(\d+\.\s|\d+\.\d+\s|\(\d+\)\s|[A-Z]\.\s|Article\s+\d+|Section\s+\d+)'
    matches = list(re.finditer(pattern, text, re.MULTILINE))
    
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        boundaries.append((start, end))
    
    return boundaries

def extract_clause_metadata(clause_text: str) -> Dict[str, str]:
    """
    Extract metadata from a clause (title, section number, etc.).
    
    Args:
        clause_text (str): Individual clause text
        
    Returns:
        Dict[str, str]: Metadata dictionary
    """
    metadata = {
        'section_number': '',
        'title': '',
        'content': clause_text
    }
    
    # Extract section number
    number_match = re.match(r'^\s*(\d+\.\d*|\(\d+\)|[A-Z]\.)\s*', clause_text)
    if number_match:
        metadata['section_number'] = number_match.group(1).strip()
    
    # Extract title (first line or first sentence)
    lines = clause_text.split('\n')
    if lines:
        first_line = lines[0].strip()
        # Remove section number from title
        if metadata['section_number']:
            first_line = first_line.replace(metadata['section_number'], '').strip()
        
        # Take first sentence as title if it's short enough
        sentences = re.split(r'[.!?]', first_line)
        if sentences and len(sentences[0]) < 100:
            metadata['title'] = sentences[0].strip()
        else:
            metadata['title'] = first_line[:50] + '...' if len(first_line) > 50 else first_line
    
    return metadata
