import os
import re
from datetime import datetime
from dotenv import load_dotenv
from github import Github, Auth

load_dotenv(dotenv_path="../.env")

GITHUB_TOKEN = os.getenv("TG_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("TG_GITHUB_REPO") or os.getenv("GITHUB_REPO")

def get_repo():
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    return g.get_repo(GITHUB_REPO)


def fix_tags_in_tf(content, resource_type, resource_name, new_tags):
    resource_pattern = rf'resource\s+"{re.escape(resource_type)}"\s+"{re.escape(resource_name)}"\s*\{{'
    resource_match = re.search(resource_pattern, content)

    if not resource_match:
        print(f"  WARNING: Could not find resource block for {resource_type}.{resource_name}")
        return None

    search_start = resource_match.start()

    next_resource = re.search(r'\nresource\s+"', content[resource_match.end():])
    if next_resource:
        search_end = resource_match.end() + next_resource.start()
    else:
        search_end = len(content)

    resource_section = content[search_start:search_end]

    tags_pattern = r'tags\s*=\s*\{[^}]*\}'
    tags_match = re.search(tags_pattern, resource_section)

    if not tags_match:
        print(f"  WARNING: Could not find tags block in {resource_type}.{resource_name}")
        return None

    indent_match = re.match(r'^(\s*)', resource_section[tags_match.start():].split('\n')[0])
    if indent_match:
        indent = indent_match.group(1)
        value_indent = indent + "  "
    else:
        indent = "  "
        value_indent = "    "

    new_tags_lines = []
    for key, value in sorted(new_tags.items()):
        new_tags_lines.append(f'{value_indent}{key} = "{value}"')

    new_tags_block = f"tags = {{\n" + "\n".join(new_tags_lines) + f"\n{indent}}}"

    abs_tags_start = search_start + tags_match.start()
    abs_tags_end = search_start + tags_match.end()

    updated_content = content[:abs_tags_start] + new_tags_block + content[abs_tags_end:]

    return updated_content

def fix_description_in_tf(content, resource_type, resource_name, new_description):
    resource_pattern = rf'resource\s+"{re.escape(resource_type)}"\s+"{re.escape(resource_name)}"\s*\{{'
    resource_match = re.search(resource_pattern, content)

    if not resource_match:
        print(f"  WARNING: Could not find resource block for {resource_type}.{resource_name}")
        return None

    search_start = resource_match.start()

    next_resource = re.search(r'\nresource\s+"', content[resource_match.end():])
    if next_resource:
        search_end = resource_match.end() + next_resource.start()
    else:
        search_end = len(content)

    resource_section = content[search_start:search_end]

    desc_pattern = r'description\s*=\s*"[^"]*"'
    desc_match = re.search(desc_pattern, resource_section)

    if not desc_match:
        print(f"  WARNING: Could not find description in {resource_type}.{resource_name}")
        return None

    indent_match = re.match(r'^(\s*)', resource_section[desc_match.start():].split('\n')[0])
    indent = indent_match.group(1) if indent_match else "  "

    new_desc_line = f'{indent}description = "{new_description}"'

    abs_start = search_start + desc_match.start()
    abs_end = search_start + desc_match.end()

    updated_content = content[:abs_start] + new_desc_line + content[abs_end:]
    return updated_content


def fix_instance_type_in_tf(content, resource_type, resource_name, new_instance_type):
    resource_pattern = rf'resource\s+"{re.escape(resource_type)}"\s+"{re.escape(resource_name)}"\s*\{{'
    resource_match = re.search(resource_pattern, content)

    if not resource_match:
        print(f"  WARNING: Could not find resource block for {resource_type}.{resource_name}")
        return None

    search_start = resource_match.start()

    next_resource = re.search(r'\nresource\s+"', content[resource_match.end():])
    if next_resource:
        search_end = resource_match.end() + next_resource.start()
    else:
        search_end = len(content)

    resource_section = content[search_start:search_end]

    type_pattern = r'instance_type\s*=\s*"[^"]*"'
    type_match = re.search(type_pattern, resource_section)

    if not type_match:
        print(f"  WARNING: Could not find instance_type in {resource_type}.{resource_name}")
        return None

    indent_match = re.match(r'^(\s*)', resource_section[type_match.start():].split('\n')[0])
    indent = indent_match.group(1) if indent_match else "  "

    new_type_line = f'{indent}instance_type = "{new_instance_type}"'

    abs_start = search_start + type_match.start()
    abs_end = search_start + type_match.end()

    updated_content = content[:abs_start] + new_type_line + content[abs_end:]
    return updated_content



def create_fix_pr(resource_address, field_name, before_value, after_value, classification="SAFE", reason="", suggestion=""):
    repo = get_repo()

    timestamp = int(datetime.now().timestamp())
    branch_name = f"terraguard-fix-{resource_address.replace('.', '-')}-{timestamp}"
    source = repo.get_branch("main")
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source.commit.sha)

    file_path = "infra/main.tf"
    file = repo.get_contents(file_path, ref=branch_name)
    current_content = file.decoded_content.decode("utf-8")

    parts = resource_address.split(".")
    resource_type = parts[0]
    resource_name = parts[1]

    if classification == "RISKY":
        updated_content = None
        fix_type = "risky-flagged"
    elif field_name in ("tags", "tags_all") and isinstance(before_value, dict):
        updated_content = fix_tags_in_tf(current_content, resource_type, resource_name, before_value)
        fix_type = "auto-fixed"
    elif field_name == "description" and isinstance(before_value, str):
        updated_content = fix_description_in_tf(current_content, resource_type, resource_name, before_value)
        fix_type = "auto-fixed"
    elif field_name == "instance_type" and isinstance(before_value, str):
        updated_content = fix_instance_type_in_tf(current_content, resource_type, resource_name, before_value)
        fix_type = "auto-fixed"
    else:
        updated_content = None
        fix_type = "flagged"

    if updated_content is None:
        if classification == "RISKY":
            todo_comment = f"\n# TODO(TerraGuard): RISKY drift on {resource_address} -- {field_name} changed -- see PR for details\n"
        else:
            todo_comment = f"\n# TODO(TerraGuard): sync '{field_name}' on {resource_address} -- see PR\n"
        updated_content = current_content + todo_comment
        if fix_type != "risky-flagged":
            fix_type = "flagged"

    if fix_type == "auto-fixed":
        status_line = "Status: Auto-fixed -- tags in main.tf have been updated to match AWS reality. Review and merge."
    elif fix_type == "risky-flagged":
        status_line = "Status: RISKY -- DO NOT MERGE without manual review. This change may have security implications."
    else:
        status_line = "Status: Flagged -- manual edit needed. See before/after values below."

    suggestion_block = ""
    if suggestion:
        suggestion_block = f"\n\n**Suggested fix:**\n\n{suggestion}"

    pr_body = (
        f"## TerraGuard Drift Detection\n\n"
        f"**Resource:** `{resource_address}`\n\n"
        f"**Field changed:** `{field_name}`\n\n"
        f"**Classification:** {classification}\n\n"
        f"**Why:** {reason}\n\n"
        f"{status_line}\n\n"
        f"**Before (current AWS reality):**\n\n"
        f"```\n{before_value}\n```\n\n"
        f"**After (what code previously said):**\n\n"
        f"```\n{after_value}\n```"
        f"{suggestion_block}\n\n"
        f"*Opened automatically by TerraGuard.*"
    )

    repo.update_file(
        path=file_path,
        message=f"TerraGuard: fix {field_name} drift on {resource_address}",
        content=updated_content,
        sha=file.sha,
        branch=branch_name
    )

    if fix_type == "risky-flagged":
        pr_title = f"[RISKY] TerraGuard: drift on {resource_address} ({field_name}) - REVIEW REQUIRED"
    else:
        pr_title = f"TerraGuard: fix {field_name} drift on {resource_address}"

    pr = repo.create_pull(
        title=pr_title,
        body=pr_body,
        head=branch_name,
        base="main"
    )

    print(f"PR created ({fix_type}): {pr.html_url}")
    return pr.html_url


if __name__ == "__main__":
    try:
        print("Starting TerraGuard PR creation...")
        create_fix_pr(
            resource_address="aws_s3_bucket.demo_bucket",
            field_name="tags",
            before_value={"Environment": "demo", "Project": "TerraGuard", "owner": "nakul-manual-test"},
            after_value={"Environment": "demo", "Project": "TerraGuard"}
        )
    except Exception as e:
        print(f"Error: {e}")