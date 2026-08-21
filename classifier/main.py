from parser import load_plan, get_drifted_resources, get_changed_fields, classify_change
from github_fixer import create_fix_pr
from slack_alerter import send_risky_alert
from drift_history import log_drift, print_history


def run_terraguard(plan_path):
    print("TerraGuard scanning for drift...\n")

    plan = load_plan(plan_path)
    drifted = get_drifted_resources(plan)

    if not drifted:
        print("No drift detected. Everything matches code.")
        return

    print(f"Found {len(drifted)} drifted resource(s)\n")

    safe_count = 0
    risky_count = 0

    for resource in drifted:
        address = resource["address"]
        resource_type = resource["type"]
        changes = get_changed_fields(resource)

        for field, diff in changes.items():
            classification, reason, suggestion = classify_change(
                resource_type, field, diff["before"], diff["after"]
            )

            print(f"  {address} -> {field} -> {classification}")
            print(f"    Reason: {reason}")
            if suggestion:
                print(f"    Suggestion: {suggestion}")

            if classification == "SAFE":
                print(f"    Creating auto-fix PR...")
                pr_url = ""
                try:
                    pr_url = create_fix_pr(address, field, diff["before"], diff["after"])
                    safe_count += 1
                    action = "auto-fixed"
                except Exception as e:
                    print(f"    PR creation failed: {e}")
                    action = "pr-failed"

                log_drift(address, resource_type, field, classification, reason, suggestion, action, pr_url)

            elif classification == "RISKY":
                print(f"    Sending Slack alert...")
                try:
                    send_risky_alert(address, field, diff["before"], diff["after"], reason, suggestion)
                except Exception as e:
                    print(f"    Slack alert failed: {e}")

                print(f"    Creating review-only PR...")
                pr_url = ""
                try:
                    pr_url = create_fix_pr(address, field, diff["before"], diff["after"], classification="RISKY", reason=reason, suggestion=suggestion)
                    risky_count += 1
                    action = "alerted"
                except Exception as e:
                    print(f"    PR creation failed: {e}")
                    action = "alert-only"

                log_drift(address, resource_type, field, classification, reason, suggestion, action, pr_url)

    print(f"\nTerraGuard scan complete:")
    print(f"  {safe_count} safe change(s) - auto-fix PRs created")
    print(f"  {risky_count} risky change(s) - Slack alerts + review PRs created")

    # Show drift history after each run
    print_history()


if __name__ == "__main__":
    run_terraguard("../infra/plan.json")