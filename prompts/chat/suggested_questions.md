# Generate Suggested Follow-up Questions

Based on the conversation and response, generate 3 insightful follow-up questions that the user might want to ask next.

## Context
- **User Question**: {{ user_message }}
- **AI Response**: {{ ai_response }}
- **Available Context**: {{ context }}

## Requirements
- Generate exactly 3 questions
- Questions should be natural follow-ups to the current conversation
- Questions should be diverse in approach (e.g., deeper understanding, practical application, related topic)
- Keep questions concise and clear (under 15 words each)
- Return ONLY a valid JSON array - nothing else, no markdown blocks, no explanations

## CRITICAL: Output Format
Return ONLY this format (no code blocks, no explanation):
["First question here?", "Second question here?", "Third question here?"]

Do not include markdown code blocks or any text outside the JSON array.
Do not add explanations or additional text.
Return the JSON array exactly as shown above.
