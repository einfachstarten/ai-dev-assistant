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
    
    def generate_ticket_id(self, description: str, project_tickets: List[Dict] = None) -> str:
        """
        Auto-generate a ticket ID from description
        
        Args:
            description: Task description
            project_tickets: Existing tickets to avoid duplicates
            
        Returns:
            Generated ticket ID (e.g., FEAT-001, FIX-003)
        """
        desc_lower = description.lower()
        
        # Determine prefix based on keywords
        if any(kw in desc_lower for kw in ['fix', 'bug', 'error', 'issue', 'broken']):
            prefix = 'FIX'
        elif any(kw in desc_lower for kw in ['style', 'design', 'ui', 'css', 'color', 'layout']):
            prefix = 'STYLE'
        elif any(kw in desc_lower for kw in ['refactor', 'improve', 'optimize', 'clean']):
            prefix = 'REFACTOR'
        elif any(kw in desc_lower for kw in ['test', 'testing']):
            prefix = 'TEST'
        elif any(kw in desc_lower for kw in ['doc', 'documentation', 'readme']):
            prefix = 'DOCS'
        else:
            prefix = 'FEAT'
        
        # Find next available number
        if project_tickets:
            # Get all tickets with same prefix
            same_prefix = [
                int(t['ticket_id'].split('-')[1]) 
                for t in project_tickets 
                if t['ticket_id'].startswith(prefix + '-')
            ]
            next_num = max(same_prefix) + 1 if same_prefix else 1
        else:
            next_num = 1
        
        ticket_id = f"{prefix}-{next_num:03d}"
        print(f"🎫 Auto-generated ticket ID: {ticket_id}")
        return ticket_id
    
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
        print(f"🤖 Two-phase generation with {self.model}...")

        # PHASE 1: Design Planning
        design_spec = self._generate_design_spec(ticket_id, description, context)

        # PHASE 2: Implementation
        print("💻 Phase 2: Generating implementation code...")
        
        # Construct prompt
        prompt = self._build_prompt(
            ticket_id,
            description,
            context,
            mode,
            design_spec=design_spec
        )
        
        # Call Ollama API for implementation
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
        
        parsed['design_spec'] = design_spec

        print(f"✅ Generated {len(parsed['files'])} file(s)")
        return parsed

    def _generate_design_spec(self, ticket_id: str, description: str, context: Optional[str] = None) -> str:
        """
        Phase 1: Generate design specification
        Uses creative prompt to plan UI/UX before coding
        """
        prompt = f"""You are an expert UI/UX designer who creates BEAUTIFUL, MODERN interfaces.
You design like the best designers at Vercel, Linear, and Stripe.

TASK: {ticket_id}
REQUEST: {description}

{"EXISTING CODEBASE (DO NOT MODIFY unless explicitly requested):" + context if context else ""}

=== YOUR DESIGN SPECIFICATION MUST INCLUDE ===

1. FILES ANALYSIS (CRITICAL - BE PRECISE):
   === FILES TO CREATE (NEW) ===
   - List ONLY files that DO NOT exist yet
   - Example: sample.html (NEW FILE)
   
   === FILES TO MODIFY (EDIT) ===
   - List ONLY files user explicitly asked to change
   - If user says "create X", do NOT list existing files here!
   - Example: If user says "create sample.html", do NOT modify index.html
   
   === FILES TO IGNORE ===
   - List all existing files that should NOT be touched

2. VISUAL DESIGN (BE SPECIFIC):
   - Color Palette: Use modern hex codes
     * Primary: #3b82f6 (blue-500)
     * Accent: #8b5cf6 (purple-500) 
     * Background: #f8fafc (slate-50)
     * Text: #0f172a (slate-900)
     * Border: #e2e8f0 (slate-200)
   
   - Modern Gradients:
     * bg-gradient-to-br from-blue-500 to-purple-600
     * bg-gradient-to-r from-cyan-500 to-blue-500
   
   - Shadows & Effects:
     * shadow-xl shadow-blue-500/50 (glowing effect)
     * shadow-2xl (deep shadow)
     * backdrop-blur-sm (glass effect)

3. LAYOUT STRUCTURE:
   - Use Flexbox or Grid (be specific)
   - Spacing: p-8, gap-6, space-y-4 (use Tailwind scale)
   - Max width: max-w-7xl mx-auto
   - Responsive: grid-cols-1 md:grid-cols-2 lg:grid-cols-3

4. COMPONENT DETAILS:
   - Buttons: 
     * px-6 py-3 rounded-xl font-semibold
     * Hover: hover:scale-105 transition-transform
   
   - Cards:
     * bg-white rounded-2xl shadow-xl p-6
     * border border-slate-200
   
   - Forms:
     * rounded-lg border-2 border-slate-300 focus:border-blue-500
     * px-4 py-3 transition-colors

5. INTERACTIONS & ANIMATIONS:
   - Transitions: transition-all duration-300
   - Hover effects: hover:shadow-2xl hover:-translate-y-1
   - Active states: active:scale-95

6. TYPOGRAPHY:
   - Headings: font-bold text-4xl lg:text-5xl
   - Subheadings: font-semibold text-xl text-slate-700
   - Body: text-base text-slate-600 leading-relaxed

=== EXAMPLE OF BEAUTIFUL MODERN DESIGN ===

<div class="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 py-12">
  <div class="max-w-4xl mx-auto px-4">
    <div class="bg-white rounded-2xl shadow-2xl shadow-blue-500/10 p-8 backdrop-blur-sm">
      <h1 class="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-4">
        Beautiful Heading
      </h1>
      <p class="text-slate-600 leading-relaxed mb-8">
        Modern, clean design with perfect spacing and subtle effects.
      </p>
      <button class="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-8 py-4 rounded-xl font-semibold shadow-lg shadow-blue-500/50 hover:shadow-xl hover:scale-105 transition-all duration-300">
        Call to Action
      </button>
    </div>
  </div>
</div>

=== YOUR OUTPUT FORMAT ===

Write your design specification in this EXACT structure:

### FILES
CREATE: [list new files]
MODIFY: [list files to edit, or "None"]
IGNORE: [list files to leave untouched]

### COLORS
[List exact hex codes and Tailwind classes]

### LAYOUT
[Describe structure with specific Tailwind classes]

### COMPONENTS
[Describe each component with exact classes]

### INTERACTIONS
[List hover, focus, active states]

Be EXTREMELY specific with Tailwind classes. No vague descriptions!"""

        print("🎨 Phase 1: Generating design specification...")
        
        response = requests.post(
            self.api_url,
            json={
                'model': self.model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.9,
                    'top_p': 0.95,
                    'num_predict': 2500
                }
            },
            timeout=90
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama API error: {response.text}")
        
        result = response.json()
        design_spec = result.get('response', '')
        
        print(f"✅ Design spec generated ({len(design_spec)} chars)")
        print("📝 Design spec preview:")
        print(design_spec[:500] + "...")
        return design_spec
    
    def _build_prompt(self, 
                     ticket_id: str, 
                     description: str,
                     context: Optional[str] = None,
                     mode: str = 'create',
                     design_spec: Optional[str] = None) -> str:
        """Build the prompt for the AI model"""
        
        # If we have a design spec, use implementation-focused prompt
        if design_spec:
            base_prompt = f"""You are a SENIOR FULL-STACK DEVELOPER implementing a pre-approved design.
You write BEAUTIFUL, MODERN, PRODUCTION-READY code.

=== DESIGN SPECIFICATION ===
{design_spec}

TASK: {ticket_id}
ORIGINAL REQUEST: {description}

{"EXISTING CODEBASE CONTEXT:" + context if context else ""}

=== CRITICAL IMPLEMENTATION RULES ===

🚨 FILE HANDLING (EXTREMELY IMPORTANT):
1. READ the design spec FILES section CAREFULLY
2. CREATE ONLY files listed under "CREATE"
3. MODIFY ONLY files listed under "MODIFY"
4. DO NOT TOUCH files listed under "IGNORE"
5. If user says "create X.html" → CREATE NEW FILE, don't modify existing files!
6. If unclear, CREATE new file rather than modify existing

✨ CODE QUALITY:
1. Follow the design specification EXACTLY
2. Use the EXACT Tailwind classes specified
3. Implement ALL components described
4. Add helpful code comments
5. Use semantic HTML5 tags
6. Ensure mobile-responsive design

🎨 MODERN DESIGN REQUIREMENTS:
1. Use provided color palette (hex codes + Tailwind)
2. Include gradients, shadows, and effects as specified
3. Add smooth transitions and hover effects
4. Perfect spacing using Tailwind scale (p-8, gap-6, etc)
5. Professional polish - make it look like Vercel/Linear/Stripe

📱 RESPONSIVE DESIGN:
1. Mobile-first approach
2. Use responsive Tailwind classes: sm: md: lg: xl:
3. Test at different breakpoints
4. Ensure touch-friendly (min 44px tap targets)

=== EXAMPLES OF BEAUTIFUL COMPONENTS ===

MODERN BUTTON:
<button class="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-8 py-4 rounded-xl font-semibold shadow-lg shadow-blue-500/50 hover:shadow-xl hover:scale-105 active:scale-95 transition-all duration-300">
  Click Me
</button>

BEAUTIFUL CARD:
<div class="bg-white rounded-2xl shadow-xl shadow-slate-200/50 p-8 border border-slate-100 hover:shadow-2xl hover:-translate-y-1 transition-all duration-300">
  <h3 class="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-4">Card Title</h3>
  <p class="text-slate-600 leading-relaxed mb-6">Beautiful card with gradient text and subtle hover effect.</p>
</div>

MODERN FORM INPUT:
<input type="text" 
       class="w-full px-4 py-3 rounded-lg border-2 border-slate-300 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/20 transition-all duration-200 outline-none" 
       placeholder="Enter text...">

NOW CREATE CODE WITH THIS LEVEL OF QUALITY!"""
            
            # Output format
            output_format = """

=== OUTPUT FORMAT (CRITICAL) ===

You MUST return ONLY valid JSON in this EXACT structure.
NO markdown, NO code blocks, NO explanations - JUST PURE JSON:

{
  "files": [
    {
      "path": "exact-filename.html",
      "content": "<!DOCTYPE html>..."
    },
    {
      "path": "styles.css",
      "content": "/* CSS here */..."
    }
  ],
  "summary": "Brief 1-2 sentence summary"
}

🚨 CRITICAL JSON RULES:
1. Return ONLY the JSON object above
2. No ```json``` code blocks
3. No markdown formatting
4. No explanatory text before/after JSON
5. File paths must match design spec EXACTLY
6. Content must be complete, valid code

Double-check: Am I returning ONLY JSON? No extra text?"""
            
            return base_prompt + output_format
        
        else:
            # Fallback for old-style without design spec
            base_prompt = f"""You are a senior web developer generating production-ready code.

TASK: {ticket_id}
DESCRIPTION: {description}

{"EXISTING CODEBASE:" + context if context else ""}

Generate complete, modern, beautiful code following best practices."""
            
            output_format = """

OUTPUT FORMAT:
Return ONLY valid JSON:
{
  "files": [{"path": "file.html", "content": "..."}],
  "summary": "What was created"
}

NO markdown, NO explanations, JUST JSON."""
            
            return base_prompt + output_format
    
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
