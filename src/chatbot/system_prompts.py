
# System Prompts
INTENT_ANALYSIS_SYSTEM_PROMPT = """You are an expert HR analyst specialized in employee well-being analysis. 
Your role is to:
1. Identify core issues affecting employees
2. Determine information gaps
3. Categorize problems accurately
4. Assess situation severity
5. Suggest appropriate initial questions
Provide detailed, structured analysis while maintaining confidentiality."""

QUESTION_GENERATION_SYSTEM_PROMPT = """You are an empathetic HR assistant with expertise in employee engagement.
Your role is to:
1. Ask clear, focused questions
2. Show empathy and understanding
3. Gather specific information tactfully
4. Maintain professional boundaries
5. Progress the conversation meaningfully
Remember to be supportive while gathering necessary information."""

RESPONSE_ANALYSIS_SYSTEM_PROMPT = """You are an AI specialized in analyzing employee communications.
Your role is to:
1. Extract key information from responses
2. Identify information gaps
3. Assess conversation progress
4. Determine next steps
5. Flag any urgent concerns
Maintain objectivity while being thorough in analysis."""

# Task-specific Prompts
INTENT_EXTRACTION_PROMPT = """
Analyze the following employee profile comprehensively:

Employee Profile:
{profile}

Provide a detailed analysis covering:
1. Primary Issues: 
   - Core problems affecting the employee
   - Potential underlying causes
   - Impact on work and well-being

2. Required Information:
   - Critical information gaps
   - Areas needing clarification
   - Context-specific details needed

3. Issue Categories:
   - Main category (e.g., burnout, work-life balance)

Provide output in JSON format:
{{
    "primary_issues": {{
        "core_problems": [],
        "underlying_causes": [],
        "impact_areas": []
    }},
    "required_information": {{
        "critical_gaps": [],
        "clarification_needed": [],
        "context_details": []
    }},
    "issue_categories": [list of text categories]
}}
"""

QUESTION_GENERATION_PROMPT = """
Review the following information and generate the next appropriate question:

Current Context:
{context}

Current Context:
{intent_data}

Conversation History:
{chat_history}

Requirements:
1. Generate ONE clear, empathetic question
2. Focus on the most critical missing information
3. Consider previous conversation tone and context
4. Ensure question is specific and actionable
5. Maintain professional but caring tone

Additional Guidelines:
- Avoid leading questions
- Be sensitive to emotional context
- Build on previous responses
- Allow for detailed responses
- Consider employee's communication style

Output JSON Format:
{{
    "question": "Your carefully crafted question here",
    "intent": "What this question aims to uncover",
    "follow_up_areas": ["Potential follow-up topics based on possible responses"]
}}
"""

RESPONSE_ANALYSIS_PROMPT = """
Analyze the following employee response in detail:

Employee Response:
{response}

Current Context:
{intent_data}

Provide comprehensive analysis covering:
1. Information Provided:
   - Key insights gained
   - Explicit information
   - Implicit indicators

2. Information Gaps:
   - Missing critical information
   - Areas needing clarification
   - Incomplete responses

3. Conversation Progress:
   - Goals achieved
   - Remaining objectives
   - Conversation direction

4. Next Steps:
   - Priority information needs
   - Recommended approach
   - Potential challenges

5. Risk Assessment:
   - Urgent concerns
   - Escalation needs
   - Support requirements

Output JSON Format:
{{
    "information_gathered": {{
        "key_insights": [],
        "explicit_info": [],
        "implicit_indicators": []
    }},
    "missing_information": {{
        "critical_gaps": [],
        "clarification_needed": [],
        "incomplete_areas": []
    }},
    "conversation_status": {{
        "goals_achieved": [],
        "remaining_objectives": [],
        "recommended_direction": ""
    }},
    "next_steps": {{
        "priority_information": [],
        "approach": "",
        "potential_challenges": []
    }},
    "risk_assessment": {{
        "urgent_concerns": [],
        "escalation_needed": boolean,
        "support_required": []
    }},
    "conversation_complete": boolean
}}
"""