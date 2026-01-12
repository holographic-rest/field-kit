Field-Kit Demo v0.2 (2–3 min)
Setup

Run:

python3 src/cli.py --data-dir prototype/data_demo_architecture eval:regression

Money Shot 1 — grounded suggestions

Run:

python3 src/cli.py --data-dir prototype/data_demo_architecture suggestions:show it_3B424DED62C74E7BA93935E7

Look for:

probabilities

evidence shards [local@0] and [mid@-4]

graph distance [d=1]

Money Shot 2 — evaluation

Run:

python3 src/cli.py --data-dir prototype/data_demo_architecture eval:dashboard

Look for:

ECR=1.0 and tests passing

Money Shot 3 — governance

Run:

python3 src/cli.py --data-dir prototype/data_demo_architecture govern:report

Look for:

recommended action + rationale (suggest-only)

Optional — backup proof

Run:

python3 src/cli.py --data-dir prototype/data_demo_architecture backup:create --output prototype/outputs/demo_backup.tar

python3 src/cli.py backup:verify prototype/outputs/demo_backup.tar