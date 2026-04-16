# AWS setup (one-time)

You do this once by hand, then GitHub Actions takes over. Total AWS cost at
this project's scale: ~$1–3/month (S3 only).

Replace `YOUR_GITHUB_USER/YOUR_REPO` and `mtg-scrape-unwindgames` below with
your values.

## 1. Create the S3 bucket

```bash
aws s3api create-bucket \
  --bucket mtg-scrape-unwindgames \
  --region us-east-1

aws s3api put-bucket-versioning \
  --bucket mtg-scrape-unwindgames \
  --versioning-configuration Status=Enabled

aws s3api put-public-access-block \
  --bucket mtg-scrape-unwindgames \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

## 2. Lifecycle rule (tier down old data)

```bash
cat > lifecycle.json <<'EOF'
{
  "Rules": [
    {
      "ID": "tier-prices",
      "Status": "Enabled",
      "Filter": { "Prefix": "prices/" },
      "Transitions": [
        { "Days": 90,  "StorageClass": "STANDARD_IA" },
        { "Days": 365, "StorageClass": "GLACIER_IR" }
      ]
    },
    {
      "ID": "tier-raw",
      "Status": "Enabled",
      "Filter": { "Prefix": "raw/" },
      "Transitions": [
        { "Days": 30,  "StorageClass": "STANDARD_IA" },
        { "Days": 180, "StorageClass": "GLACIER_IR" }
      ]
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
  --bucket mtg-scrape-unwindgames \
  --lifecycle-configuration file://lifecycle.json
```

## 3. GitHub OIDC provider in IAM (one-time per account)

If you already added `token.actions.githubusercontent.com` as an OIDC
provider, skip this.

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

## 4. IAM role for GitHub Actions

Trust policy — restricts which repo can assume the role:

```bash
cat > trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_USER/YOUR_REPO:*"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
  --role-name mtg-scrape-ingest \
  --assume-role-policy-document file://trust.json
```

Inline permission policy — write-only to the bucket:

```bash
cat > perms.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:HeadObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::mtg-scrape-unwindgames",
        "arn:aws:s3:::mtg-scrape-unwindgames/*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name mtg-scrape-ingest \
  --policy-name s3-write \
  --policy-document file://perms.json
```

## 5. Wire GitHub → AWS

In the GitHub repo settings:

- **Settings → Secrets and variables → Actions → Secrets → New repository secret**
  - `AWS_ROLE_ARN` = `arn:aws:iam::YOUR_ACCOUNT_ID:role/mtg-scrape-ingest`
- **Settings → Secrets and variables → Actions → Variables → New repository variable**
  - `MTG_S3_BUCKET` = `mtg-scrape-unwindgames`
  - `AWS_REGION` = `us-east-1`

## 6. Run the backfill

After pushing, kick off the seed run manually:

- GitHub **Actions** tab → **backfill** workflow → **Run workflow** → branch `main`.

That pulls the 90-day `AllPrices.json.xz` and fans out into 90 daily Parquet
partitions on S3. Then `daily-ingest` takes over at 03:30 UTC.

## 7. Verify

```bash
aws s3 ls s3://mtg-scrape-unwindgames/prices/ --recursive | head
aws s3 ls s3://mtg-scrape-unwindgames/state/mtgjson/
```

## Cost sanity check

At steady state (one year in): ~30 GB of Parquet on S3 Standard transitioning
to IA at 90d and Glacier IR at 365d. Total monthly AWS: ~$1–3. GitHub Actions
runner time: ~2 min/day, free on public repos / well inside the 2000-min
private-repo allowance.
