import json
import os
import sys
from llm_classifier import llm_classify
# Fields that commonly differ due to state format, not real drift
IGNORE_FIELDS = {
    "force_destroy",
    "bucket",
    "name",
    "name_prefix",
    "revoke_rules_on_delete",
    "egress",
    "tags_all",
    "arn",
    "id",
    "owner_id",
    "vpc_id",
    "bucket_domain_name",
    "bucket_regional_domain_name",
    "hosted_zone_id",
    "region",
    "request_payer",
    "acceleration_status",
    "bucket_prefix",
    "policy",
    "acl",
    "object_lock_enabled",
    "versioning_configuration",
}

# --- Load the plan.json file ---
def load_plan(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

#before = current live AWS reality, after = what your Terraform code wants it to become

# --- Extract only resources that actually changed ---
def get_drifted_resources(plan_data):
    drifted = []
    resource_changes = plan_data.get("resource_changes", [])

    for resource in resource_changes:
        actions = resource["change"]["actions"]

        # Skip resources with no real change
        if actions == ["no-op"] or actions == ["read"]:
            continue

        drifted.append(resource)

    return drifted


# --- Compare before/after and figure out exactly which fields changed ---
def get_changed_fields(resource):
    before = resource["change"]["before"] or {}
    after = resource["change"]["after"] or {}

    changed_fields = {}
    all_keys = set(before.keys()) | set(after.keys())

    for key in all_keys:
        if key in IGNORE_FIELDS:
            continue
        if before.get(key) != after.get(key):
            changed_fields[key] = {
                "before": before.get(key),
                "after": after.get(key)
            }

    return changed_fields

# --- Classification rules ---
# --- Classification rules ---
def classify_change(resource_type, field_name, before_value, after_value):

    if field_name in ("tags", "tags_all", "description"):
        return "SAFE", "Tags and descriptions are cosmetic changes", ""

    if resource_type == "aws_instance" and field_name == "instance_type":
        return "SAFE", "Instance type is a performance setting, not security", ""

    if resource_type == "aws_security_group" and field_name == "ingress":
        before_rules = before_value or []
        risky_ports = [22, 3389, 3306, 5432]

        for rule in before_rules:
            cidr_blocks = rule.get("cidr_blocks", [])
            from_port = rule.get("from_port")
            if "0.0.0.0/0" in cidr_blocks and from_port in risky_ports:
                return "RISKY", f"Port {from_port} is open to the entire internet", f"Either restrict port {from_port} to a specific IP range in main.tf, or run terraform apply to close public access immediately."

        return "SAFE", "Network change but not on a sensitive port", ""

    if resource_type.startswith("aws_iam_"):
        return "RISKY", "IAM changes always require human review", "Review who made this change and why. If intentional, update IAM policy in main.tf. If unauthorized, run terraform apply to revert and investigate the source."

    if resource_type == "aws_s3_bucket_server_side_encryption_configuration":
        return "RISKY", "Encryption settings affect data protection", "Verify encryption is still enabled. If disabled, run terraform apply immediately to re-enable. If changed to a different algorithm, update main.tf if intentional."

    if resource_type == "aws_s3_bucket_public_access_block":
        return "RISKY", "Public access changes can expose private data", "Check if the bucket is now publicly accessible. Run terraform apply to restore access restrictions immediately if this was unintended."

    if resource_type == "aws_s3_bucket_versioning" and field_name == "versioning_configuration":
        return "SAFE", "Versioning is a data retention setting", ""

        # --- Rule: CloudWatch log retention ---
    if resource_type == "aws_cloudwatch_log_group" and field_name == "retention_in_days":
        return "SAFE", "Log retention is a storage setting, not security", ""

    # --- Default: ask LLM for ambiguous cases ---
    classification, reason, suggestion = llm_classify(resource_type, field_name, before_value, after_value)
    return "RISKY", reason, suggestion

    # --- Default: ask LLM for ambiguous cases ---
    classification, reason, suggestion = llm_classify(resource_type, field_name, before_value, after_value)
    return "RISKY", reason, suggestion

if __name__ == "__main__":
    plan = load_plan("../infra/plan.json")
    drifted = get_drifted_resources(plan)

    print(f"Found {len(drifted)} drifted resource(s)\n")

    for resource in drifted:
        print(f"Resource: {resource['address']} ({resource['type']})")
        changes = get_changed_fields(resource)

        for field, diff in changes.items():
            classification = classify_change(
                resource["type"], field, diff["before"], diff["after"]
            )
            print(f"  Field changed: {field} -> {classification}")
            print(f"    before: {diff['before']}")
            print(f"    after:  {diff['after']}")
        print()