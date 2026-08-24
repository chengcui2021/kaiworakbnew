# Deployment (EC2 + ECR + SSM)

Pushes to **`main`** run [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml): test → build/push images → SSM deploy on EC2.

## Flow

1. CI validates the Docker Compose stack and `/health`.
2. Deploy builds and pushes backend + frontend images to ECR.
3. Deploy assumes the GitHub OIDC IAM role and runs `aws ssm send-command` on the target instance.
4. On the host: `git pull`, ECR login, `docker compose -f docker-compose.prod.yml pull`, then `up -d`.

## GitHub secrets

Repository secret:

| Secret | Purpose |
|---|---|
| `AWS_ROLE_TO_ASSUME` | OIDC role for ECR push and SSM deploy |

Production environment secrets:

| Secret | Purpose |
|---|---|
| `DEPLOY_INSTANCE_ID` | EC2 instance id for SSM deploy |
| `DEPLOY_PATH` | Repo path on host, default `/opt/metamorphic-kb` |

## One-time server setup

1. Install Docker, Docker Compose v2, Git and AWS CLI.
2. Clone the repository to `/opt/metamorphic-kb` or the configured `DEPLOY_PATH`.
3. Copy `.env.example` to `.env` and set runtime values.
4. Ensure the instance is managed by AWS Systems Manager.
5. Attach an instance role that can pull the ECR images.

## Manual deploy

```bash
cd /opt/metamorphic-kb
git pull --ff-only origin main
export REGISTRY_HOST="613602870295.dkr.ecr.eu-central-1.amazonaws.com"
export AWS_REGION="eu-central-1"
export API_IMAGE="$REGISTRY_HOST/metamorphic-kb-api:latest"
export WEB_IMAGE="$REGISTRY_HOST/metamorphic-kb-web:latest"
./scripts/deploy.sh
```

## Verify

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:3000
```
