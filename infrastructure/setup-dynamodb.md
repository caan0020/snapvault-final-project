# Amazon DynamoDB setup

SnapVault stores all of its metadata (albums and photos) in **DynamoDB**,
a fully-managed NoSQL key–value store. We chose DynamoDB over a
relational database because the data model is tiny and the access
patterns are simple lookups by id — exactly what a key–value store is
best at — and because it needs **no server, no VPC and no firewall
rules**, which makes the Cloud9 → Elastic Beanstalk deploy a config
change rather than a networking exercise.

## Tables

Two on-demand tables, one per entity, each with a single **string
partition key called `id`**:

| Table | Partition key | Holds |
|---|---|---|
| `SnapVault-Albums` | `id` (S) | album name, created_at, share_token |
| `SnapVault-Photos` | `id` (S) | album_id, title, description, tags, favorite, file_key, file_name, content_type, size, created_at |

`Photos.album_id` is the link back to an album (the NoSQL equivalent of a
foreign key). Listing the photos of an album is a `scan` with a filter on
`album_id`; the data set for a class project is small enough that this is
instant.

**Every attribute is stored as a string.** That keeps the boto3
marshalling trivial — no `Decimal` juggling for numbers, no boolean type
surprises (the `favorite` flag is `"0"` / `"1"`). Conversions happen in
`app/models.py`.

## Billing mode

`PAY_PER_REQUEST` (on-demand). There is no provisioned capacity to size
or pay for when idle — ideal for a demo that is mostly idle.

## How the app talks to it

All reads and writes go through `app/repos/dynamo.py`, using the boto3
DynamoDB *resource* API:

| Operation | boto3 call | Used by |
|---|---|---|
| read one | `table.get_item(Key={"id": id})` | open an album / photo |
| read many | `table.scan()` (+ `FilterExpression`) | lists, search, favorites |
| write | `table.put_item(Item=...)` | create / update (upsert) |
| delete | `table.delete_item(Key={"id": id})` | delete album / photo |

The same generic `DynamoRepo` class is instantiated twice — once per
table — so there is exactly one place that knows how to talk to DynamoDB.

## Creating the tables

Idempotent script (safe to re-run):

```bash
python3 infrastructure/init_dynamodb.py
```

It calls `create_table` for any table that doesn't exist yet, then waits
until both are `ACTIVE`. Equivalent AWS CLI for one table:

```bash
aws dynamodb create-table \
  --table-name SnapVault-Albums \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST --region us-east-1
```

## Permissions

The Elastic Beanstalk EC2 instance reads/writes DynamoDB using the
**`LabInstanceProfile`** role, which already grants DynamoDB access in
the Learner Lab. No access keys live in the code or the environment.

## Screenshots to capture

- `05-dynamodb-tables.png` — the two tables in the DynamoDB console.
- `06-dynamodb-items.png` — `SnapVault-Photos → Explore items` showing
  rows created by the app.
