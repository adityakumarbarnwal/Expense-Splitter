"""
Prompt builder for the AI expense parser.

This module constructs controlled, structured prompts for Gemini.
The prompt design:
1. Instructs the model to return ONLY valid JSON
2. Provides group context (member names) to limit hallucination
3. Instructs the model to use null for uncertain fields
4. Instructs the model NOT to guess member names
"""

import json


EXPENSE_PARSE_SYSTEM_PROMPT = """You are an expense parsing assistant for a group expense splitting app.

Your ONLY job is to extract expense information from natural language text and return it as valid JSON.

CRITICAL RULES:
1. Return ONLY valid JSON. No explanation, no markdown, no code blocks.
2. If you cannot confidently extract a field, use null.
3. NEVER guess or invent member names. Only use names from the provided member list.
4. NEVER calculate splits or shares — that is done by the application.
5. The "participants" array should include everyone who shares the expense (including the payer if applicable).
6. Resolve pronouns like "I", "me", "myself" to the current_member name if provided.
7. If the amount is ambiguous or missing, use null.
8. If the payer is ambiguous, use null.

JSON Schema to follow:
{
  "description": string or null,  // What the expense was for (e.g., "Dinner", "Groceries")
  "amount": number or null,       // Total amount as a number (e.g., 1200, not "1200" or "₹1200")
  "payer": string or null,        // Name of who paid (must match a name from the members list)
  "participants": array of strings, // Names of everyone sharing the expense (from members list only)
  "confidence": "high" | "medium" | "low",  // Your confidence in the extraction
  "notes": string or null         // Any ambiguities, clarifications, or issues
}
"""


def build_expense_parse_prompt(
    text: str,
    member_names: list[str],
    current_member_name: str | None = None,
) -> str:
    """
    Build the user-facing prompt for expense parsing.

    Args:
        text: The natural language expense description from the user.
        member_names: List of actual member names in the group.
        current_member_name: Name of the member entering the expense (for pronoun resolution).

    Returns:
        The user prompt to send to the model.
    """
    context_parts = []

    if member_names:
        context_parts.append(f"Group members: {json.dumps(member_names)}")

    if current_member_name:
        context_parts.append(
            f"Current member (resolve 'I', 'me', 'myself' to this name): {current_member_name!r}"
        )

    context = "\n".join(context_parts)

    return f"""{context}

Expense description from user:
"{text}"

Extract the expense information and return valid JSON only."""
