#!/usr/bin/env python3
"""
Ollama AI Integration
Handles code generation using local Ollama models
"""

import json
import requests
from typing import Dict, List, Optional
from context_selector import SmartContextSelector, RelevantFile


class OllamaCodeGenerator:
    def __init__(self, model='qwen2.5-coder:7b', base_url='http://localhost:11434'):
        """
        Initialize Ollama code generator
        
        Args:
            model: Ollama model name
            base_url: Ollama API base URL
        """
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
    
    def generate_code(self, 
                     ticket_id: str, 
                     description: str,
                     context: Optional[str] = None,
                     mode: str = 'create') -> Dict:
        """
        Generate code based on ticket description
        
        Args:
            ticket_id: Ticket identifier (e.g., FEAT-001)
            description: Natural language description of what to build
            context: Optional repository context (existing files)
            mode: 'create' for new files, 'edit' for modifying existing
            
        Returns:
            Dict with 'files' list and 'summary' string
        """
        print(f"🤖 Generating code with {self.model}...")
        
        # Construct prompt
        prompt = self._build_prompt(ticket_id, description, context, mode)
        
        # Call Ollama API
        response = requests.post(
            self.api_url,
            json={
                'model': self.model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'num_predict': 4000  # Allow longer responses
                }
            },
            timeout=120  # 2 minute timeout
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama API error: {response.text}")
        
        # Parse response
        result = response.json()
        ai_output = result.get('response', '')
        
        # Extract and parse JSON from AI output
        parsed = self._parse_ai_output(ai_output)
        
        print(f"✅ Generated {len(parsed['files'])} file(s)")
        return parsed
    
    def _build_prompt(self, 
                     ticket_id: str, 
                     description: str,
                     context: Optional[str] = None,
                     mode: str = 'create') -> str:
        """Build the prompt for the AI model"""
        
        # Base prompt parts
        base_prompt = f"""You are a senior web developer. """
        
        # Add context if provided
        context_section = ""
        if context:
            context_section = f"""

EXISTING CODEBASE CONTEXT:
{context}

IMPORTANT: Use the existing code style, patterns, and conventions from the codebase above.
"""
        
        # Different prompts for create vs edit mode
        if mode == 'edit':
            task_instruction = f"""Modify the existing code to implement this change:

TICKET: {ticket_id}
CHANGE REQUEST: {description}

REQUIREMENTS:
1. Study the existing code carefully
2. Make minimal, focused changes
3. Preserve existing functionality
4. Follow the established code patterns
5. Update only what's necessary
6. Maintain code quality and style
7. Add comments explaining changes"""
        else:
            task_instruction = f"""Generate complete, production-ready code for this task:

TICKET: {ticket_id}
TASK: {description}

REQUIREMENTS:
1. Generate ALL necessary files (HTML, CSS, JavaScript)
2. Use modern web development best practices
3. Create visually appealing UI with good design
4. Include helpful comments in the code
5. Ensure responsive design (mobile-friendly)
6. Use semantic HTML5
7. Add proper meta tags and structure"""
        
        # Output format instruction
        output_format = """

OUTPUT FORMAT:
You MUST return ONLY valid JSON in this EXACT structure (no markdown, no code blocks, no explanations):

{
  "files": [
    {
      "path": "index.html",
      "content": "<!DOCTYPE html>..."
    },
    {
      "path": "style.css",
      "content": "body { ... }"
    },
    {
      "path": "script.js",
      "content": "console.log(...);"
    }
  ],
  "summary": "Brief 1-2 sentence summary of what was created/changed"
}

CRITICAL: Return ONLY the JSON object above, nothing else. No markdown formatting, no explanations, just pure JSON."""
        
        return base_prompt + context_section + task_instruction + output_format
    
    def _build_prompt_old(self, ticket_id: str, description: str) -> str:
        """Build the prompt for the AI model (old version for reference)"""
        return f"""You are a senior web developer. Generate complete, production-ready code for this task:

TICKET: {ticket_id}
TASK: {description}

REQUIREMENTS:
1. Generate ALL necessary files (HTML, CSS, JavaScript)
2. Use modern web development best practices
3. Create visually appealing UI with good design
4. Include helpful comments in the code
5. Ensure responsive design (mobile-friendly)
6. Use semantic HTML5
7. Add proper meta tags and structure

OUTPUT FORMAT:
You MUST return ONLY valid JSON in this EXACT structure (no markdown, no code blocks, no explanations):

{{
  "files": [
    {{
      "path": "index.html",
      "content": "<!DOCTYPE html>..."
    }},
    {{
      "path": "style.css",
      "content": "body {{ ... }}"
    }},
    {{
      "path": "script.js",
      "content": "console.log(...);"
    }}
  ],
  "summary": "Brief 1-2 sentence summary of what was created"
}}

CRITICAL: Return ONLY the JSON object above, nothing else. No markdown formatting, no explanations, just pure JSON."""
    
    def _parse_ai_output(self, output: str) -> Dict:
        """Parse AI output to extract JSON"""
        # Try different extraction methods
        
        # Method 1: Direct JSON parse
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass
        
        # Method 2: Extract from code blocks
        if '```json' in output:
            start = output.find('```json') + 7
            end = output.find('```', start)
            json_str = output[start:end].strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Method 3: Extract first JSON object
        import re
        json_match = re.search(r'\{[\s\S]*"files"[\s\S]*\}', output)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Method 4: Build minimal structure if parsing fails
        print("⚠️  Warning: Could not parse AI output as JSON, creating fallback...")
        
        # Return a basic structure
        return {
            'files': [
                {
                    'path': 'index.html',
                    'content': f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Page</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
        }}
        h1 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>AI Generated Content</h1>
    <p>Task: {output[:200]}...</p>
    <p><em>Note: AI output parsing failed, this is a fallback template.</em></p>
</body>
</html>'''
                }
            ],
            'summary': 'Fallback HTML page created (AI output parsing failed)'
        }
    
    def is_ollama_available(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code != 200:
                return False
            
            # Check if model is available
            data = response.json()
            models = [m.get('name', '') for m in data.get('models', [])]
            return any(self.model in m for m in models)
        except:
            return False


def test_ollama():
    """Test function"""
    generator = OllamaCodeGenerator()
    
    # Check availability
    if not generator.is_ollama_available():
        print("❌ Ollama not available or model not installed")
        return
    
    # Test generation
    result = generator.generate_code(
        'TEST-001',
        'Create a simple button that changes color when clicked'
    )
    
    print(f"✅ Generated {len(result['files'])} files")
    print(f"Summary: {result['summary']}")


if __name__ == '__main__':
    test_ollama()
