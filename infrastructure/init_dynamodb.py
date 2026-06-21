"""Create the DynamoDB tables SnapVault needs — idempotent.

Run once from the Cloud9 terminal (credentials are already present there):

    python3 infrastructure/init_dynamodb.py

It creates two on-demand (pay-per-request) tables, each with a single
string partition key called `id`:

    SnapVault-Albums
    SnapVault-Photos

Re-running is safe: tables that already exist are left untouched. Table
names and region can be overridden with the same environment variables
the app uses (AWS_REGION, SNAPVAULT_ALBUMS_TABLE, SNAPVAULT_PHOTOS_TABLE).
"""
import os

import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLES = [
    os.environ.get("SNAPVAULT_ALBUMS_TABLE", "SnapVault-Albums"),
    os.environ.get("SNAPVAULT_PHOTOS_TABLE", "SnapVault-Photos"),
]


def main():
    ddb = boto3.client("dynamodb", region_name=REGION)
    existing = ddb.list_tables().get("TableNames", [])

    for name in TABLES:
        if name in existing:
            print("- %s already exists, skipping" % name)
            continue
        print("- creating %s ..." % name)
        ddb.create_table(
            TableName=name,
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        )

    waiter = ddb.get_waiter("table_exists")
    for name in TABLES:
        waiter.wait(TableName=name)
        print("- %s is ACTIVE" % name)

    print("\nDynamoDB is ready: %s" % ", ".join(TABLES))


if __name__ == "__main__":
    main()
