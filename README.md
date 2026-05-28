# Homepage Provisioner

A GitHub Actions pipeline that automatically provisions an AWS EC2 instance running
[Homepage](https://gethomepage.dev) — a self-hosted dashboard — with a weather widget
configured for your city.

Push a change to `config/provision.yml` and the pipeline deploys (or redeploys) your
server automatically.

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| git | any | https://git-scm.com |
| Python | 3.10+ | https://python.org |
| AWS CLI | 2.x | https://aws.amazon.com/cli/ |
| Terraform | 1.5+ | `brew install hashicorp/tap/terraform` |

You also need:
- An AWS account with an IAM user that has EC2 and S3 permissions
- A GitHub account
- A free OpenWeatherMap API key (https://openweathermap.org/api)

---

## Setup

### 1. Fork / clone this repository

```bash
git clone https://github.com/YOUR_USERNAME/homepage-provisioner.git
cd homepage-provisioner
```

### 2. Create an IAM user in AWS

1. Open the AWS Console → IAM → Users → Create user
2. Name it `homepage-deployer`
3. Attach the policy **AmazonEC2FullAccess** and **AmazonS3FullAccess**
4. After creation, go to Security credentials → Create access key
5. Choose "Application running outside AWS"
6. Save the Access Key ID and Secret Access Key — you will not see the secret again

### 3. Create an S3 bucket for Terraform state

Terraform records everything it creates in a state file. We store it in S3 so
GitHub Actions and your local machine share the same view.

```bash
# Replace MY-BUCKET-NAME with something globally unique, e.g. homepage-tf-state-yourname-2024
aws s3 mb s3://MY-BUCKET-NAME --region us-east-1

# Enable versioning so you can recover from accidental state corruption
aws s3api put-bucket-versioning \
  --bucket MY-BUCKET-NAME \
  --versioning-configuration Status=Enabled
```

### 4. Create an SSH key pair in AWS

```bash
# Creates the key pair and saves the private key locally
aws ec2 create-key-pair \
  --key-name homepage-key \
  --query 'KeyMaterial' \
  --output text \
  --region us-east-1 > ~/.ssh/homepage-key.pem

chmod 400 ~/.ssh/homepage-key.pem
```

If you use a different region, replace `us-east-1` in both commands above and set
`region` in `config/provision.yml` to match.

### 5. Sign up for OpenWeatherMap

1. Go to https://openweathermap.org/api and create a free account
2. Navigate to API keys and copy your key
3. Note: new API keys can take up to 2 hours to activate

### 6. Edit config/provision.yml

```yaml
region: us-east-1              # AWS region (must match your SSH key region)
instance_type: t2.micro        # Free tier eligible
server_name: my-homepage       # Used as the Name tag on all AWS resources
openweathermap_api_key: YOUR_KEY_HERE
city: New York                 # Any city OpenWeatherMap recognises
ssh_key_name: homepage-key     # Must match the key pair name you created in step 4
```

### 7. Create a GitHub repository and add secrets

Create a new repository on GitHub, then add these secrets under
Settings → Secrets and variables → Actions → New repository secret:

| Secret name | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Your IAM user access key ID |
| `AWS_SECRET_ACCESS_KEY` | Your IAM user secret access key |
| `AWS_REGION` | e.g. `us-east-1` |
| `TF_STATE_BUCKET` | The S3 bucket name from step 3 |
| `TF_STATE_REGION` | The region the S3 bucket is in (e.g. `us-east-1`) |

### 8. Push to GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/homepage-provisioner.git
git add .
git commit -m "Initial setup"
git push -u origin main
```

The pipeline will not trigger on this push because `config/provision.yml` has a
placeholder API key. Once you add your real key and push again, it will run.

### 9. Watch it run

Go to your GitHub repository → Actions tab. You will see a workflow run in progress.
When it finishes, click the run and look at the Summary section for your server's URL
and SSH command.

The server takes about 3–5 minutes after the pipeline completes to finish its first-boot
setup (installing Docker, pulling container images). If the URL shows nothing immediately,
wait a few minutes and refresh.

---

## How to SSH into the server

```bash
# The exact command is shown in the pipeline Summary after each run
ssh -i ~/.ssh/homepage-key.pem ubuntu@YOUR_SERVER_IP
```

To check the first-boot log:

```bash
sudo cat /var/log/user_data.log
```

---

## How to update your dashboard

Edit `config/provision.yml` (change city, API key, etc.) and push to main.
The pipeline runs again and reprovisioning the server with the new config.

To edit dashboard layout, SSH into the server and edit files under
`/opt/homepage/config/`, then run:

```bash
cd /opt/homepage && docker compose restart homepage
```

---

## How to destroy the infrastructure

To shut down the server and delete all AWS resources created by Terraform:

```bash
cd terraform

# Initialise Terraform locally with your state bucket
terraform init \
  -backend-config="bucket=YOUR-BUCKET-NAME" \
  -backend-config="region=us-east-1" \
  -backend-config="key=homepage/terraform.tfstate"

# Preview what will be deleted
terraform plan -destroy -var-file=terraform.tfvars

# Delete everything
terraform destroy -var-file=terraform.tfvars
```

> **Note:** The S3 state bucket itself is not managed by Terraform and will not be
> deleted by `terraform destroy`. Delete it manually in the AWS console if you no
> longer need it.

---

## Architecture

```
config/provision.yml  ←  you edit this
        │
        ▼
scripts/generate_config.py
        │  generates
        ├──▶ homepage/config/settings.yaml
        ├──▶ homepage/config/widgets.yaml   (contains city + API key)
        ├──▶ homepage/config/services.yaml
        └──▶ terraform/terraform.tfvars
                  │
                  ▼
            Terraform (main.tf)
                  │  provisions
                  ├──▶ Security Group  (ports 22, 80, 443)
                  ├──▶ EC2 Instance    (Ubuntu 22.04)
                  └──▶ Elastic IP      (fixed public address)
                              │
                              ▼ user_data.sh runs on first boot
                        Docker Compose
                              ├──▶ Homepage  (port 3000, internal only)
                              └──▶ Nginx     (port 80, proxies → Homepage)
```
