import os
import json
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")

SLACK_WEBHOOK = os.getenv("TG_SLACK_WEBHOOK") or os.getenv("SLACK_WEBHOOK")


def send_risky_alert(resource_address, field_name, before_value, after_value):
    message = {
        "text": (
            f"--- RISKY DRIFT DETECTED ---\n\n"
            f"*Resource:* `{resource_address}`\n"
            f"*Field changed:* `{field_name}`\n"
            f"*Classification:* RISKY - NOT auto-fixed\n\n"
            f"*Current AWS state (before):*\n"
            f"```{json.dumps(before_value, indent=2)}```\n\n"
            f"*What code expects (after):*\n"
            f"```{json.dumps(after_value, indent=2)}```\n\n"
            f"This change was NOT auto-fixed. Please review immediately."
        )
    }

    response = requests.post(SLACK_WEBHOOK, json=message)

    if response.status_code == 200:
        print(f"Slack alert sent for {resource_address}")
    else:
        print(f"Slack alert failed: {response.status_code} {response.text}")


if __name__ == "__main__":
    # Test with your actual security group drift example
    send_risky_alert(
        resource_address="aws_security_group.demo_sg",
        field_name="ingress",
        before_value=[{
            "cidr_blocks": ["0.0.0.0/0"],
            "from_port": 22,
            "to_port": 22,
            "protocol": "tcp",
            "description": "HTTPS from anywhere"
        }],
        after_value=[{
            "cidr_blocks": ["0.0.0.0/0"],
            "from_port": 443,
            "to_port": 443,
            "protocol": "tcp",
            "description": "HTTPS from anywhere"
        }]
    )