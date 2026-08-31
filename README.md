# TerraGuard 🛡️

> An automated bot that watches your AWS infrastructure every 6 hours, catches unauthorized manual changes, fixes harmless ones by itself via GitHub Pull Requests, and alerts your team on Slack about dangerous ones — before they become security incidents.

---

## The Problem

In companies using Terraform (Infrastructure-as-Code), all cloud resources are supposed to be managed through code. But in practice, engineers make quick manual changes directly in the AWS console — opening a port, adding a tag, tweaking a setting — and forget to update the code afterward.

This gap between code and reality is called **drift**. It's dangerous because it's invisible. Nobody knows about it until something breaks, or worse, until a security audit discovers that someone accidentally left SSH open to the entire internet weeks earlier.

**TerraGuard catches this automatically.**

---

## How It Works

```
Every 6 hours (automated via GitHub Actions):

1. terraform plan -json
   → Compares your Terraform code against real AWS infrastructure
   → Generates a structured diff (plan.json)

2. Python parser reads plan.json
   → Finds every resource that drifted
   → Isolates exactly which fields changed (before vs after)

3. Classifier checks each change against a rule table:
   → SAFE  (tags, descriptions, non-security settings)
   → RISKY (open ports, IAM changes, disabled encryption)
   → UNKNOWN → Mistral AI LLM analyzes and explains

4. Based on classification:
   SAFE  → Bot edits main.tf, opens a GitHub PR with the fix done
   RISKY → Slack alert with fix suggestion + review-only GitHub PR

5. Every event logged to SQLite drift history database
```

---

## Demo

### SAFE drift detected — auto-fix PR opened

Someone adds a tag `Team = platform-engineering` to the S3 bucket manually in the AWS console.

TerraGuard detects it, edits `main.tf` to add the tag, and opens a PR:

```
✅ PR #56: TerraGuard: fix tags drift on aws_s3_bucket.demo_bucket
   Files changed: infra/main.tf
   + Team = "platform-engineering"
   Status: Auto-fixed — review and merge
```

### RISKY drift detected — Slack alert + review PR

Someone opens SSH (port 22) to the entire internet on a security group.

TerraGuard fires immediately:

```
⚠️ RISKY DRIFT DETECTED

Resource: aws_security_group.demo_sg
Field changed: ingress
Why: Port 22 is open to the entire internet

Current AWS state: port 22, open to 0.0.0.0/0
What code expects: port 443, open to 0.0.0.0/0

Suggested fix: Either restrict port 22 to a specific IP range
in main.tf, or run terraform apply to close public access immediately.

This change was NOT auto-fixed. Please review immediately.
```

And opens a `[RISKY] REVIEW REQUIRED` PR on GitHub for the audit trail.

### Drift history

```
========== TerraGuard Drift History ==========

Total events: 3
Safe: 1  |  Risky: 2  |  Auto-fixed: 1

Timestamp              Resource                    Field      Class    Action
-----------------------------------------------------------------------------
2026-08-21T19:39:36    aws_security_group.demo_sg  ingress    RISKY    alerted
2026-08-21T19:39:29    aws_s3_bucket.demo_bucket   tags       SAFE     auto-fixed
2026-08-21T19:10:39    aws_security_group.demo_sg  ingress    RISKY    alerted
```

---

## Classification Rules

The core design decision: **anything that changes who can access what is always flagged for a human. Everything else can be automated.**

| Resource | Field | Classification | Action |
|---|---|---|---|
| Any resource | tags / tags_all | SAFE | Auto-fix PR |
| Any resource | description | SAFE | Auto-fix PR |
| aws_instance | instance_type | SAFE | Auto-fix PR |
| aws_security_group | ingress (port 22/3389/3306/5432 to 0.0.0.0/0) | RISKY | Slack alert + review PR |
| aws_security_group | ingress (non-sensitive port) | SAFE | Auto-fix PR |
| aws_iam_* | any field | RISKY | Slack alert + review PR |
| aws_s3_bucket_server_side_encryption_configuration | any field | RISKY | Slack alert + review PR |
| aws_s3_bucket_public_access_block | any field | RISKY | Slack alert + review PR |
| aws_s3_bucket_versioning | versioning_configuration | SAFE | Auto-fix PR |
| aws_cloudwatch_log_group | retention_in_days | SAFE | Auto-fix PR |
| Any resource | policy | RISKY | Slack alert + review PR |
| Any resource | acl | RISKY | Slack alert + review PR |
| Unknown resource type | any field | RISKY (LLM analyzes) | Slack alert + review PR with explanation |

---

## Tech Stack

| Tool | Purpose |
|---|---|
| **Terraform** | Infrastructure-as-Code — defines AWS resources, detects drift via `terraform plan -json` |
| **AWS** | Cloud provider — S3, EC2 Security Groups monitored for drift |
| **Python 3.12** | Core language for all detection, classification, and automation logic |
| **PyGithub** | Creates branches, commits code fixes, opens Pull Requests via GitHub API |
| **GitHub Actions** | Runs the full pipeline automatically every 6 hours on a schedule |
| **Slack Webhooks** | Sends real-time RISKY drift alerts to the team's #drift-alerts channel |
| **Mistral AI** | LLM fallback — analyzes unknown resource types, provides reason + fix suggestion |
| **SQLite** | Drift history database — logs every event with timestamp, classification, action |
| **S3 Remote Backend** | Shared Terraform state — ensures both local and GitHub Actions runner see the same state |

---

## Project Structure

```
terraguard/
    .github/
        workflows/
            drift-check.yml         # GitHub Actions — runs every 6 hours
    infra/
        main.tf                     # Terraform resource definitions
        backend.tf                  # S3 remote state backend config
        .terraform.lock.hcl         # Provider version lock file
    classifier/
        parser.py                   # Loads plan.json, diffs resources, classifies SAFE/RISKY
        github_fixer.py             # Edits main.tf, creates branches, opens PRs via GitHub API
        slack_alerter.py            # Sends Slack alerts for RISKY drift
        llm_classifier.py           # Mistral AI fallback for unknown resource types
        drift_history.py            # SQLite audit log for all drift events
        main.py                     # Master orchestrator — runs the full pipeline
    .env                            # Local secrets (gitignored — never committed)
    .gitignore
```

---

## Setup

### Prerequisites

- AWS account (free tier works)
- Terraform installed
- Python 3.12+
- GitHub account
- Slack workspace
- Mistral AI API key (free tier)

### Step 1: Clone the repo

```bash
git clone https://github.com/Nakulnk098/terraguard.git
cd terraguard
```

### Step 2: Set up AWS credentials

Create an IAM user with these policies:
- `AmazonS3FullAccess`
- `AmazonEC2FullAccess`
- `IAMReadOnlyAccess`

Configure the AWS CLI:
```bash
aws configure
# Enter your Access Key ID, Secret Access Key, region (ap-south-1), output format (json)
```

### Step 3: Create the S3 state bucket

```bash
aws s3 mb s3://terraguard-state-YOUR-NAME-2026 --region ap-south-1
```

Update `infra/backend.tf` with your bucket name.

### Step 4: Deploy the demo infrastructure

```bash
cd infra
terraform init
terraform apply
```

This creates the S3 bucket and security group that TerraGuard will monitor.

### Step 5: Set up your `.env` file

Create `.env` in the root folder:

```
GITHUB_TOKEN=ghp_your_personal_access_token
GITHUB_REPO=yourusername/terraguard
SLACK_WEBHOOK=https://hooks.slack.com/services/your/webhook/url
MISTRAL_API_KEY=your_mistral_api_key
```

### Step 6: Install Python dependencies

```bash
cd classifier
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate # Mac/Linux
pip install PyGithub python-dotenv requests
```

### Step 7: Add GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions:

| Secret name | Value |
|---|---|
| `GH_PAT_TOKEN` | Your GitHub Personal Access Token |
| `MY_REPO` | `yourusername/terraguard` |
| `AWS_ACCESS_KEY_ID` | Your AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key |
| `SLACK_WEBHOOK` | Your Slack webhook URL |
| `MISTRAL_API_KEY` | Your Mistral API key |

### Step 8: Run manually

```bash
cd infra
terraform plan -out=tfplan
terraform show -json tfplan | Set-Content -Encoding UTF8 plan.json  # Windows
# OR
terraform show -json tfplan > plan.json  # Mac/Linux

cd ../classifier
python main.py
```

### Step 9: Automate

Push to GitHub. The workflow in `.github/workflows/drift-check.yml` will automatically run every 6 hours.

You can also trigger it manually: GitHub repo → Actions → TerraGuard Drift Check → Run workflow.

---

## Testing It

### Create a SAFE drift (auto-fixed)

1. Go to AWS Console → S3 → your bucket → Properties → Tags → Edit
2. Add a tag: `Team = platform-engineering`
3. Run `python main.py` (or let the scheduled job catch it)
4. Watch a PR appear on GitHub with the fix already applied

### Create a RISKY drift (Slack alert)

1. Go to AWS Console → EC2 → Security Groups → your security group
2. Inbound rules → Edit → Add rule → SSH → Anywhere-IPv4
3. Run `python main.py`
4. Watch a Slack alert fire in `#drift-alerts` with a fix suggestion
5. Run `terraform apply` to revert it

---

## Key Design Decisions

**Why rule-based classification instead of full AI?**
Rules are fast, free, auditable, and never hallucinate. An LLM making autonomous decisions about security group rules could cause real harm. Rules handle known cases reliably; the LLM is only a fallback for unknown resource types — and even then, it advises rather than decides.

**Why open a PR for RISKY changes if the code isn't fixed?**
Audit trail. A PR creates permanent, reviewable evidence that the drift was detected and acknowledged on a specific date. Security teams and compliance auditors need this paper trail.

**Why S3 remote backend?**
Without it, the Terraform state file only exists on your laptop. GitHub Actions runs on a fresh machine with no state file — it would think no resources exist and generate false drift everywhere. S3 gives both machines the same state.

**Why Mistral's HTTP API instead of the Python SDK?**
The Mistral SDK had breaking import changes across versions. Direct `requests.post()` calls work regardless of library version and never break on updates.

---

## What's Next

- [x] Add more AWS resources (CloudWatch, SSM Parameter, S3 public access block)
- [x] Flag `policy` and `acl` field changes as RISKY instead of ignoring them (previously silently skipped — a bucket made public via ACL or policy produced no alert at all)
- [ ] Expand auto-fix to more field types beyond tags/description/instance_type
- [x] Add a web dashboard for drift history visualization (static page at `docs/index.html`, regenerated and committed by the workflow every run, served via GitHub Pages)
- [ ] Slack slash command to query drift history (`/terraguard history`)
- [ ] Multi-account AWS support

---

## Resume Bullet

> Built TerraGuard, an automated Terraform drift-detection tool that scans AWS infrastructure every 6 hours via GitHub Actions, classifies changes by risk level using deterministic rules + Mistral AI LLM fallback, auto-opens GitHub PRs to fix safe drift, and sends real-time Slack alerts with fix suggestions for risky changes — with a full audit trail in SQLite and a live dashboard published automatically via GitHub Pages.

---

*Built by Nakul N | DevOps Portfolio Project*
