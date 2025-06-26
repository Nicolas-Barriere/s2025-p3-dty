"""
Content parsers for processing Albert API responses.

This module handles parsing and structuring of content responses from Albert API.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class ContentParser:
    """Parser for Albert API content responses."""
    
    @staticmethod
    def parse_summary_content(content: str) -> Dict[str, Any]:
        """
        Parse content response from Albert API to extract structured summary information.
        
        Args:
            content: Raw content response from Albert API
            
        Returns:
            Dictionary with structured summary data
        """
        summary_data = {
            'summary': content,
            'key_points': [],
            'action_required': False,
            'urgency_level': 'medium'
        }
        
        # Try to extract key points if content is structured
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('- ') or line.startswith('• ') or ('**' in line and ':' in line):
                # Extract key points from bullet points or bold sections
                clean_point = line.replace('- ', '').replace('• ', '').replace('**', '').strip()
                if clean_point and len(clean_point) > 5:
                    summary_data['key_points'].append(clean_point)
        
        # Detect urgency keywords
        content_lower = content.lower()
        if any(word in content_lower for word in ['urgent', 'immédiat', 'critique', 'panne', 'problème']):
            summary_data['urgency_level'] = 'high'
            summary_data['action_required'] = True
        elif any(word in content_lower for word in ['demande', 'besoin', 'aide', 'support']):
            summary_data['action_required'] = True
            summary_data['urgency_level'] = 'medium'
        else:
            summary_data['urgency_level'] = 'low'
            
        return summary_data

    @staticmethod
    def parse_classification_content(content: str, categories: List[str]) -> Dict[str, Any]:
        """
        Parse content response from Albert API to extract classification information.
        
        Args:
            content: Raw content response from Albert API
            categories: Available categories for classification
            
        Returns:
            Dictionary with classification data
        """
        content_lower = content.lower()
        
        # Try to extract category from content first - look for explicit classifications
        detected_category = 'normal'  # default
        confidence_score = 0.7  # default moderate confidence
        
        # Look for explicit category declarations (most reliable)
        if '**catégorie**' in content_lower:
            # Extract the category mentioned after **catégorie**
            lines = content.split('\n')
            for line in lines:
                if '**catégorie**' in line.lower():
                    if 'information' in line.lower():
                        detected_category = 'information'
                        confidence_score = 0.9
                    elif 'urgent' in line.lower():
                        detected_category = 'urgent'
                        confidence_score = 0.9
                    elif 'request' in line.lower() or 'demande' in line.lower():
                        detected_category = 'request'
                        confidence_score = 0.9
                    elif 'complaint' in line.lower() or 'plainte' in line.lower():
                        detected_category = 'complaint'
                        confidence_score = 0.9
                    elif 'support' in line.lower():
                        detected_category = 'support'
                        confidence_score = 0.9
                    elif 'low_priority' in line.lower() or 'faible' in line.lower():
                        detected_category = 'low_priority'
                        confidence_score = 0.9
                    elif 'spam' in line.lower():
                        detected_category = 'spam'
                        confidence_score = 0.9
                    break
        
        # If no explicit category found, look for patterns in the content
        if detected_category == 'normal':
            if 'félicitation' in content_lower and 'excellent' in content_lower:
                detected_category = 'low_priority'
                confidence_score = 0.8
            elif 'panne' in content_lower and 'urgent' in content_lower:
                detected_category = 'urgent'
                confidence_score = 0.9
            elif 'information' in content_lower and 'fournit' in content_lower:
                detected_category = 'information'
                confidence_score = 0.8
            elif 'demande' in content_lower and 'aide' in content_lower:
                detected_category = 'request'
                confidence_score = 0.8
        
        # Ensure detected category is in available categories
        available_cats = [cat.value if hasattr(cat, 'value') else str(cat) for cat in categories]
        if detected_category not in available_cats:
            detected_category = 'normal'
            confidence_score = 0.5
        
        return {
            'primary_category': detected_category,
            'confidence_score': confidence_score,
            'reasoning': f'Classification basée sur l\'analyse du contenu: {content[:100]}...',
            'content_analysis': content
        }

    @staticmethod
    def parse_answer_content(content: str, tone: str) -> Dict[str, Any]:
        """
        Parse content response from Albert API to extract answer information.
        
        Args:
            content: Raw content response from Albert API
            tone: Requested tone for the response
            
        Returns:
            Dictionary with response data
        """
        # Generate a subject based on content and tone
        content_lines = content.strip().split('\n')
        first_line = content_lines[0] if content_lines else content
        
        # Generate appropriate subject
        if 'merci' in content.lower():
            subject = 'Réponse à votre message'
        elif 'information' in content.lower():
            subject = 'Informations demandées'
        elif 'aide' in content.lower() or 'support' in content.lower():
            subject = 'Support technique'
        else:
            subject = 'Réponse'
        
        return {
            'response': content,
            'subject': subject,
            'tone_used': tone,
            'content_type': 'generated_response'
        }
