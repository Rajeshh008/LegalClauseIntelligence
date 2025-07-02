import os
import json
import logging
from typing import List, Dict, Any
from google import genai
from google.genai import types

# Initialize Gemini client with API key
def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    return genai.Client(api_key=api_key)

# Global client variable
client = None

def analyze_clauses_with_gemini(clauses: List[str]) -> List[Dict[str, Any]]:
    """
    Analyze a list of clauses using Gemini AI to classify, summarize, and flag risks.
    
    Args:
        clauses (List[str]): List of clause texts to analyze
        
    Returns:
        List[Dict[str, Any]]: List of analyzed clause data
    """
    analyzed_clauses = []
    
    for i, clause_text in enumerate(clauses):
        try:
            logging.info(f"Analyzing clause {i+1}/{len(clauses)}")
            analysis = analyze_single_clause(clause_text)
            
            clause_data = {
                'original_text': clause_text,
                'clause_type': analysis.get('clause_type', 'Unknown'),
                'summary': analysis.get('summary', 'No summary available'),
                'risk_flag': analysis.get('risk_flag', False),
                'risk_reason': analysis.get('risk_reason', ''),
                'confidence': analysis.get('confidence', 0.0)
            }
            
            analyzed_clauses.append(clause_data)
            
        except Exception as e:
            logging.error(f"Error analyzing clause {i+1}: {str(e)}")
            # Add fallback analysis for failed clauses
            clause_data = {
                'original_text': clause_text,
                'clause_type': 'Unknown',
                'summary': 'Analysis failed - manual review required',
                'risk_flag': True,
                'risk_reason': 'Could not analyze with AI - requires manual review',
                'confidence': 0.0
            }
            analyzed_clauses.append(clause_data)
    
    return analyzed_clauses

def analyze_single_clause(clause_text: str) -> Dict[str, Any]:
    """
    Analyze a single clause using Gemini AI.
    
    Args:
        clause_text (str): The clause text to analyze
        
    Returns:
        Dict[str, Any]: Analysis results including type, summary, and risk assessment
    """
    try:
        # Initialize client if not already done
        global client
        if client is None:
            client = get_gemini_client()
        
        # Load the prompt template
        prompt = load_legal_analysis_prompt()
        
        # Format the prompt with the clause text
        formatted_prompt = prompt.format(clause_text=clause_text)
        
        # Generate analysis using Gemini
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=formatted_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,  # Low temperature for consistent analysis
                max_output_tokens=1000,
            )
        )
        
        if not response.text:
            raise ValueError("Empty response from Gemini API")
        
        # Parse the response
        analysis = parse_gemini_response(response.text)
        
        # Add additional risk detection based on keywords
        additional_risks = detect_keyword_based_risks(clause_text)
        if additional_risks and not analysis.get('risk_flag', False):
            analysis['risk_flag'] = True
            analysis['risk_reason'] = additional_risks
        
        return analysis
        
    except Exception as e:
        logging.error(f"Error in Gemini analysis: {str(e)}")
        raise

def load_legal_analysis_prompt() -> str:
    """
    Load the legal analysis prompt template.
    
    Returns:
        str: The prompt template
    """
    prompt_path = "prompts/legal_analysis_prompt.txt"
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Return default prompt if file not found
        return get_default_legal_analysis_prompt()

def get_default_legal_analysis_prompt() -> str:
    """
    Get the default legal analysis prompt.
    
    Returns:
        str: Default prompt template
    """
    return """
You are a legal analysis AI assistant. Analyze the following legal contract clause and provide a structured response.

Instructions:
1. Identify the clause type (e.g., Termination, Liability, Confidentiality, Payment, IP Rights, etc.)
2. Provide a plain English summary that a non-lawyer can understand
3. Assess if there are any significant legal risks or red flags
4. Provide reasoning for any risk flags

Be objective and focus on potential power imbalances, hidden conditions, or unusual terms that could disadvantage one party.

Clause to analyze:
{clause_text}

Please respond in the following JSON format:
{{
    "clause_type": "The type of legal clause",
    "summary": "Plain English explanation of what this clause means and does",
    "risk_flag": true/false,
    "risk_reason": "Explanation of why this clause might be risky (only if risk_flag is true)",
    "confidence": 0.85
}}

Ensure your response is valid JSON and nothing else.
"""

def parse_gemini_response(response_text: str) -> Dict[str, Any]:
    """
    Parse the Gemini response into structured data.
    
    Args:
        response_text (str): Raw response from Gemini
        
    Returns:
        Dict[str, Any]: Parsed analysis data
    """
    try:
        # Clean the response text
        cleaned_response = response_text.strip()
        
        # Remove markdown code blocks if present
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3]
        
        cleaned_response = cleaned_response.strip()
        
        # Parse JSON
        analysis = json.loads(cleaned_response)
        
        # Validate required fields
        required_fields = ['clause_type', 'summary', 'risk_flag']
        for field in required_fields:
            if field not in analysis:
                analysis[field] = get_default_value(field)
        
        # Ensure risk_reason is present if risk_flag is True
        if analysis.get('risk_flag', False) and not analysis.get('risk_reason'):
            analysis['risk_reason'] = 'Potential risk detected but no specific reason provided'
        
        # Set default confidence if not provided
        if 'confidence' not in analysis:
            analysis['confidence'] = 0.7
        
        return analysis
        
    except json.JSONDecodeError:
        # Fallback parsing for non-JSON responses
        return parse_non_json_response(response_text)

def parse_non_json_response(response_text: str) -> Dict[str, Any]:
    """
    Fallback parser for non-JSON responses from Gemini.
    
    Args:
        response_text (str): Raw response text
        
    Returns:
        Dict[str, Any]: Parsed analysis data
    """
    analysis = {
        'clause_type': 'Unknown',
        'summary': 'Could not parse AI response properly',
        'risk_flag': False,
        'risk_reason': '',
        'confidence': 0.5
    }
    
    # Try to extract information using regex patterns
    import re
    
    # Extract clause type
    type_match = re.search(r'(?:clause type|type):\s*([^\n]+)', response_text, re.IGNORECASE)
    if type_match:
        analysis['clause_type'] = type_match.group(1).strip()
    
    # Extract summary
    summary_match = re.search(r'(?:summary|explanation):\s*([^\n]+(?:\n[^\n:]+)*)', response_text, re.IGNORECASE)
    if summary_match:
        analysis['summary'] = summary_match.group(1).strip()
    
    # Check for risk indicators
    risk_keywords = ['risk', 'danger', 'concern', 'warning', 'caution', 'problematic']
    if any(keyword in response_text.lower() for keyword in risk_keywords):
        analysis['risk_flag'] = True
        analysis['risk_reason'] = 'Potential risks mentioned in analysis'
    
    return analysis

def get_default_value(field: str) -> Any:
    """
    Get default value for a field.
    
    Args:
        field (str): Field name
        
    Returns:
        Any: Default value
    """
    defaults = {
        'clause_type': 'Unknown',
        'summary': 'No summary available',
        'risk_flag': False,
        'risk_reason': '',
        'confidence': 0.5
    }
    return defaults.get(field, '')

def detect_keyword_based_risks(clause_text: str) -> str:
    """
    Detect risks based on keyword patterns and legal red flags.
    
    Args:
        clause_text (str): Clause text to analyze
        
    Returns:
        str: Risk description if found, empty string otherwise
    """
    clause_lower = clause_text.lower()
    
    # High-risk keywords and patterns
    risk_patterns = {
        'auto_renewal': {
            'keywords': ['auto-renew', 'automatically renew', 'automatic renewal', 'evergreen'],
            'description': 'Automatic renewal clause - may lock you into ongoing commitments'
        },
        'exclusivity': {
            'keywords': ['exclusive', 'solely', 'only work with', 'exclusively'],
            'description': 'Exclusivity clause - may limit your business opportunities'
        },
        'unlimited_liability': {
            'keywords': ['unlimited liability', 'no limit to liability', 'fully liable'],
            'description': 'Unlimited liability - you could be responsible for significant damages'
        },
        'indemnification': {
            'keywords': ['indemnify', 'hold harmless', 'defend and hold'],
            'description': 'Indemnification clause - you may be required to cover legal costs and damages'
        },
        'broad_termination': {
            'keywords': ['terminate at will', 'terminate without cause', 'immediate termination'],
            'description': 'Broad termination rights - the other party can end the agreement easily'
        },
        'ip_assignment': {
            'keywords': ['assign all rights', 'transfer ownership', 'work for hire'],
            'description': 'Intellectual property assignment - you may lose rights to your work'
        },
        'penalty_clauses': {
            'keywords': ['penalty', 'liquidated damages', 'substantial damages'],
            'description': 'Penalty clause - you may face financial penalties for breach'
        },
        'governing_law': {
            'keywords': ['governed by laws of', 'jurisdiction of', 'courts of'],
            'description': 'Jurisdiction clause - legal disputes may need to be resolved in unfavorable location'
        },
        'modification_restrictions': {
            'keywords': ['cannot be modified', 'no modifications', 'written consent required'],
            'description': 'Modification restrictions - agreement may be difficult to change later'
        },
        'confidentiality_overreach': {
            'keywords': ['perpetual confidentiality', 'permanent non-disclosure', 'indefinite confidentiality'],
            'description': 'Excessive confidentiality terms - may restrict your business activities indefinitely'
        }
    }
    
    detected_risks = []
    
    for risk_type, risk_data in risk_patterns.items():
        if any(keyword in clause_lower for keyword in risk_data['keywords']):
            detected_risks.append(risk_data['description'])
    
    return '; '.join(detected_risks) if detected_risks else ''

def calculate_overall_risk_score(analyzed_clauses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate an overall risk score for the contract.
    
    Args:
        analyzed_clauses (List[Dict[str, Any]]): List of analyzed clauses
        
    Returns:
        Dict[str, Any]: Risk score and summary
    """
    if not analyzed_clauses:
        return {'score': 0, 'level': 'Unknown', 'summary': 'No clauses to analyze'}
    
    total_clauses = len(analyzed_clauses)
    risky_clauses = sum(1 for clause in analyzed_clauses if clause.get('risk_flag', False))
    
    risk_percentage = (risky_clauses / total_clauses) * 100
    
    if risk_percentage >= 50:
        risk_level = 'High'
    elif risk_percentage >= 25:
        risk_level = 'Medium'
    elif risk_percentage > 0:
        risk_level = 'Low'
    else:
        risk_level = 'Minimal'
    
    summary = f"{risky_clauses} out of {total_clauses} clauses flagged as potentially risky ({risk_percentage:.1f}%)"
    
    return {
        'score': risk_percentage,
        'level': risk_level,
        'summary': summary,
        'risky_clause_count': risky_clauses,
        'total_clause_count': total_clauses
    }
