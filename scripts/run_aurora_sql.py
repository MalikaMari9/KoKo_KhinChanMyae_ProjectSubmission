import boto3

# ---- CONFIG: UPDATE ONLY IF YOUR VALUES CHANGE ----
REGION = "us-east-1"
CLUSTER_ARN = "arn:aws:rds:us-east-1:061468768569:cluster:my-aurora-serverless"
SECRET_ARN = "arn:aws:secretsmanager:us-east-1:061468768569:secret:my-aurora-serverless-S33o50"
DATABASE_NAME = "myapp"
SQL_FILE = "scripts/aurora_sql.sql"  # this should be in the same folder as this script
# ---------------------------------------------------


def load_sql_statements(path: str):
    """Load SQL file and split into individual statements by ';'."""
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Very simple split by ';' – good enough for typical lab schema scripts
    raw_statements = sql.split(";")
    statements = [stmt.strip() for stmt in raw_statements if stmt.strip()]

    return statements


def main():
    rds_data = boto3.client("rds-data", region_name=REGION)

    statements = load_sql_statements(SQL_FILE)
    print(f"Loaded {len(statements)} SQL statements from {SQL_FILE}")

    for i, stmt in enumerate(statements, start=1):
        print(f"\nExecuting statement {i}/{len(statements)}:")
        # Print only first 120 chars so logs are not insane
        print(stmt[:120].replace("\n", " ") + ("..." if len(stmt) > 120 else ""))

        response = rds_data.execute_statement(
            resourceArn=CLUSTER_ARN,
            secretArn=SECRET_ARN,
            database=DATABASE_NAME,
            sql=stmt,
        )

        # Optional: print number of records affected
        updated = response.get("numberOfRecordsUpdated")
        if updated is not None:
            print(f" -> numberOfRecordsUpdated = {updated}")
        else:
            print(" -> executed (no row count returned)")

    print("\n✅ All SQL statements executed successfully via Data API.")


if __name__ == "__main__":
    main()
