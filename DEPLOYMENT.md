# Deployment

## Live Environment
- Platform: AWS EC2 (free tier)
- Instance type: t3.micro
- AMI: Ubuntu Server 24.04 LTS
- Region: ap-south-1 (Mumbai)
- Availability Zone: ap-south-1a
- IAM Role: ec2-s3-readonly-role (least-privilege, read-only access only)
- Security Group: SSH (port 22) restricted to a single trusted IP — no open inbound access
- Deployed: 21 June 2026

## How It Runs
1. SSH into the instance
2. Activate the project's Python virtual environment
3. Run `python3 business_workflow_agent.py` to start a new report
4. The agent pauses before the human-approval step and writes its state to a local SQLite checkpoint
5. Resume with `python3 business_workflow_agent.py --resume <thread_id>` to review and approve/reject
6. Every decision — approved or rejected — is recorded in `audit_log.json`

## Why EC2, No Docker
Deployment runs directly via a Python virtual environment on Ubuntu, kept deliberately simple for a free-tier single-instance setup. No container orchestration is in scope at this stage.

## Note on Public IP
This instance doesn't have a static (Elastic) IP, so its address changes if the instance is ever stopped and restarted — for that reason it isn't hardcoded here. Check the AWS EC2 console under "Public IPv4 address" for the current value.