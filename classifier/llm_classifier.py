import os
import json
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


def llm_classify(resource_type, field_name, before_value, after_value):
    if not MISTRAL_API_KEY:
        print("    No Mistral API key found, defaulting to RISKY")
        return "RISKY", "No LLM available for analysis", "No suggestion available"

    prompt = (
        f"You are a cloud infrastructure security analyst. "
        f"A Terraform-managed AWS resource has drifted from its code.\n\n"
        f"Resource type: {resource_type}\n"
        f"Field changed: {field_name}\n"
        f"Before (current AWS state): {json.dumps(before_value, default=str)}\n"
        f"After (what code expects): {json.dumps(after_value, default=str)}\n\n"
        f"Do three things:\n"
        f"1. Classify this drift as SAFE or RISKY\n"
        f"2. Explain why in one sentence\n"
        f"3. Suggest how to fix this in 2-3 sentences. Include both options: "
        f"how to accept the change (update code to match reality) and "
        f"how to revert it (restore original state)\n\n"
        f"Respond in exactly this format:\n"
        f"CLASSIFICATION: SAFE or RISKY\n"
        f"REASON: one sentence\n"
        f"SUGGESTION: 2-3 sentences"
    )

    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-small-latest",
                "messages": [{"role": "user", "content": prompt}]
            }
        )

        data = response.json()
        result = data["choices"][0]["message"]["content"].strip()

        if "CLASSIFICATION: SAFE" in result:
            classification = "SAFE"
        else:
            classification = "RISKY"

        reason_start = result.find("REASON:")
        suggestion_start = result.find("SUGGESTION:")

        if reason_start != -1 and suggestion_start != -1:
            reason = result[reason_start + 7:suggestion_start].strip()
            suggestion = result[suggestion_start + 11:].strip()
        elif reason_start != -1:
            reason = result[reason_start + 7:].strip()
            suggestion = "Review the change manually and decide whether to update code or revert AWS."
        else:
            reason = result
            suggestion = "Review the change manually and decide whether to update code or revert AWS."

        print(f"    LLM analysis: {classification} - {reason}")
        print(f"    LLM suggestion: {suggestion}")
        return classification, reason, suggestion

    except Exception as e:
        print(f"    LLM call failed: {e}, defaulting to RISKY")
        return "RISKY", f"LLM error: {e}", "Review the change manually."