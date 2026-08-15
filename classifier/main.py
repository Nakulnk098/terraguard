from parser import load_plan, get_drifted_resources, get_changed_fields, classify_change
from github_fixer import create_fix_pr
from slack_alerter import send_risky_alert


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
            classification = classify_change(
                resource_type, field, diff["before"], diff["after"]
            )

            print(f"  {address} -> {field} -> {classification}")

            if classification == "SAFE":
                print(f"    Creating auto-fix PR...")
                try:
                    create_fix_pr(address, field, diff["before"], diff["after"])
                    safe_count += 1
                except Exception as e:
                    print(f"    PR creation failed: {e}")

            elif classification == "RISKY":
                print(f"    Sending Slack alert...")
                try:
                    send_risky_alert(address, field, diff["before"], diff["after"])
                except Exception as e:
                    print(f"    Slack alert failed: {e}")

                print(f"    Creating review-only PR...")
                try:
                    create_fix_pr(address, field, diff["before"], diff["after"], classification="RISKY")
                    risky_count += 1
                except Exception as e:
                    print(f"    PR creation failed: {e}")

    print(f"\nTerraGuard scan complete:")
    print(f"  {safe_count} safe change(s) - auto-fix PRs created")
    print(f"  {risky_count} risky change(s) - Slack alerts + review PRs created")


if __name__ == "__main__":
    run_terraguard("../infra/plan.json")