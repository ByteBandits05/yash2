# ============================================================
# FILE: smoketest/smoke_test.py
# PURPOSE: Databricks OIDC Smoke Test Script for Table Existence and Row Count
# DESCRIPTION: Connects to Databricks using OIDC credentials from environment variables,
#              validates that a specified table exists and contains at least one row.
# ============================================================

import os
import sys
import logging
from databricks import sql

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("smoke_test")

def get_env(var, required=True, default=None):
    value = os.getenv(var, default)
    if required and not value:
        logger.error(f"Missing required environment variable: {var}")
        sys.exit(1)
    return value

def connect_databricks(host, client_id, client_secret, tenant_id):
    try:
        logger.info("Establishing connection to Databricks via OIDC...")
        connection = sql.connect(
            server_hostname=host.replace("https://", "").replace(":443", ""),
            http_path="/sql/1.0/warehouses/",
            access_token=None,
            auth_type="azure-oauth",
            azure_client_id=client_id,
            azure_client_secret=client_secret,
            azure_tenant_id=tenant_id,
        )
        logger.info("Databricks connection established.")
        return connection
    except Exception as e:
        logger.error(f"Failed to connect to Databricks: {str(e)}")
        sys.exit(2)

def check_table_and_data(connection, table_name):
    try:
        with connection.cursor() as cursor:
            # Check if table exists
            schema, _, table = table_name.partition(".")
            schema = schema if table else "default"
            table = table or schema
            table_exists_query = (
                f"SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_schema = '{schema}' AND table_name = '{table}'"
            )
            cursor.execute(table_exists_query)
            exists = cursor.fetchone()[0]
            if exists == 0:
                logger.error(f"Table '{table_name}' does not exist.")
                return False
            logger.info(f"Table '{table_name}' exists.")
            # Check if table has rows
            row_count_query = f"SELECT COUNT(*) FROM {table_name}"
            cursor.execute(row_count_query)
            row_count = cursor.fetchone()[0]
            if row_count == 0:
                logger.error(f"Table '{table_name}' exists but contains no data.")
                return False
            logger.info(f"Table '{table_name}' has {row_count} rows.")
            return True
    except Exception as e:
        logger.error(f"Smoke test failed: {str(e)}")
        return False

def main():
    logger.info("Starting Databricks smoke test...")
    host = get_env("DATABRICKS_HOST")
    client_id = get_env("AZURE_CLIENT_ID")
    client_secret = get_env("AZURE_CLIENT_SECRET")
    tenant_id = get_env("AZURE_TENANT_ID")
    table_name = get_env("TARGET_TABLE_NAME", required=False, default="default.sample_table")

    conn = connect_databricks(host, client_id, client_secret, tenant_id)
    success = check_table_and_data(conn, table_name)
    try:
        conn.close()
    except Exception:
        pass
    if success:
        logger.info("SMOKE TEST PASSED.")
        sys.exit(0)
    else:
        logger.error("SMOKE TEST FAILED.")
        sys.exit(3)

if __name__ == "__main__":
    main()
