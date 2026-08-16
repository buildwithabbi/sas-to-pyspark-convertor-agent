import re
import sqlglot
from sqlglot import transpile, parse_one, exp


class SQLParser:
    """Parses SAS PROC SQL queries and translates them to PySpark SQL / DataFrames."""

    def __init__(self):
        pass

    def translate_proc_sql(self, raw_proc_sql: str) -> str:
        """Translates a full PROC SQL block into clean PySpark code."""
        queries = self._extract_sql_statements(raw_proc_sql)
        pyspark_lines = []

        for q in queries:
            q_clean = self._clean_sas_sql_features(q)
            try:
                # Transpile ANSI/SAS SQL to PySpark SQL dialect using sqlglot
                transpiled = transpile(q_clean, read="postgres", write="spark")[0]
                create_table_match = re.search(r'(?i)CREATE\s+TABLE\s+([a-zA-Z0-9_\.]+)\s+AS\s+(.*)', q_clean, re.DOTALL)
                if create_table_match:
                    target_table = create_table_match.group(1).replace('.', '_')
                    select_sql = create_table_match.group(2).strip()

                    # Transpile the select statement
                    spark_select = transpile(select_sql, read="postgres", write="spark")[0]
                    pyspark_lines.append(f"{target_table} = spark.sql(\"\"\"\n{spark_select}\n\"\"\")")
                    pyspark_lines.append(f"{target_table}.createOrReplaceTempView(\"{target_table}\")")
                else:
                    pyspark_lines.append(f"spark.sql(\"\"\"\n{transpiled}\n\"\"\")")

            except Exception:
                # Fallback to direct string conversion with PySpark spark.sql()
                cleaned_query = re.sub(r'(?i)\bPROC\s+SQL\s*;', '', q).strip()
                cleaned_query = re.sub(r'(?i)\bQUIT\s*;', '', cleaned_query).strip()

                create_m = re.search(r'(?i)CREATE\s+TABLE\s+([a-zA-Z0-9_\.]+)\s+AS\s*(.*)', cleaned_query, re.DOTALL)
                if create_m:
                    tbl = create_m.group(1).replace('.', '_')
                    sql_body = create_m.group(2).strip().rstrip(';')
                    pyspark_lines.append(f"{tbl} = spark.sql(\"\"\"\n{sql_body}\n\"\"\")")
                    pyspark_lines.append(f"{tbl}.createOrReplaceTempView(\"{tbl}\")")
                else:
                    pyspark_lines.append(f"spark.sql(\"\"\"\n{cleaned_query.rstrip(';')}\n\"\"\")")

        return "\n\n".join(pyspark_lines)

    def _extract_sql_statements(self, raw_code: str) -> list[str]:
        """Extracts individual SQL queries inside PROC SQL ... QUIT;"""
        code = re.sub(r'(?i)^\s*PROC\s+SQL\s*[^;]*;', '', raw_code)
        code = re.sub(r'(?i)QUIT\s*;', '', code)

        # Split queries by semicolon
        raw_statements = code.split(';')
        queries = []
        for s in raw_statements:
            s_clean = s.strip()
            if s_clean and any(kw in s_clean.upper() for kw in ('SELECT', 'CREATE', 'INSERT', 'UPDATE', 'DELETE', 'DROP')):
                queries.append(s_clean)
        return queries

    def _clean_sas_sql_features(self, query: str) -> str:
        """Converts SAS-specific PROC SQL syntax into standard SQL compliant with PySpark."""
        # Replace CALCULATE keyword
        query = re.sub(r'(?i)\bCALCULATE\b', '', query)
        # Replace TODAY() / NOW() / DATE()
        query = re.sub(r'(?i)\bTODAY\(\)', 'CURRENT_DATE()', query)
        query = re.sub(r'(?i)\bNOW\(\)', 'CURRENT_TIMESTAMP()', query)
        query = re.sub(r'(?i)\bDATE\(\)', 'CURRENT_DATE()', query)
        # Remove FORMAT= and INFORMAT= attributes in SELECT
        query = re.sub(r'(?i)\bFORMAT\s*=\s*[^\s,]+', '', query)
        query = re.sub(r'(?i)\bINFORMAT\s*=\s*[^\s,]+', '', query)
        query = re.sub(r'(?i)\bLABEL\s*=\s*\'[^\']*\'', '', query)
        return query
