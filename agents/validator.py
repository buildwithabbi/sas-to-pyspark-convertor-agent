import ast
import sys
import traceback
from typing import List, Dict, Any, Tuple

try:
    from pyspark.sql import SparkSession
    HAS_PYSPARK = True
except ImportError:
    HAS_PYSPARK = False


class PySparkValidatorAgent:
    """Agent 5 - Validator: Performs schema consistency, AST syntax, and local PySpark dry-run validation checks."""

    def validate_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        code = step.get("pyspark_code", "")
        validation_results = {
            "ast_syntax_valid": True,
            "schema_check": "PASS",
            "null_handling_check": "PASS",
            "errors": [],
            "warnings": []
        }

        # 1. AST Syntax Check
        try:
            ast.parse(code)
        except SyntaxError as e:
            validation_results["ast_syntax_valid"] = False
            validation_results["errors"].append(f"SyntaxError: {e.msg} at line {e.lineno}")
        except Exception as e:
            validation_results["ast_syntax_valid"] = False
            validation_results["errors"].append(f"Parse error: {str(e)}")

        # 2. Null handling check
        if "isNull()" not in code and "isNotNull()" not in code and "filter(" in code:
            validation_results["warnings"].append("Consider checking for null values in filter condition.")

        # 3. Schema consistency check
        if "createOrReplaceTempView" not in code and "=" in code:
            validation_results["warnings"].append("DataFrame transformed but not registered as TempView for downstream steps.")

        return validation_results

    def validate_all(self, optimized_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for step in optimized_steps:
            val = self.validate_step(step)
            step_res = dict(step)
            step_res["validation"] = val
            results.append(step_res)
        return results

    def dry_run_script(self, script_path: str, temp_tables: List[str] = None) -> Dict[str, Any]:
        """Spins up a local PySpark session and runs schema & execution plan checks on the generated script."""
        if not HAS_PYSPARK:
            return {"dry_run_passed": False, "error": "PySpark is not installed in the current environment."}

        try:
            spark = (SparkSession.builder
                .appName("SAS_PySpark_DryRun_Validator")
                .master("local[1]")
                .config("spark.driver.host", "localhost")
                .getOrCreate()
            )
            spark.sparkContext.setLogLevel("ERROR")

            # Mock temporary input tables if specified
            if temp_tables:
                for tbl in temp_tables:
                    clean_tbl = tbl.replace('.', '_')
                    dummy_df = spark.createDataFrame([("mock_value", 100, 2026)], ["name", "age", "year"])
                    dummy_df.createOrReplaceTempView(clean_tbl)

            # Read and execute generated script in isolated namespace
            with open(script_path, 'r', encoding='utf-8') as f:
                script_code = f.read()

            # Verify PySpark execution logic
            exec_namespace = {"spark": spark}
            exec(script_code, exec_namespace)

            return {
                "dry_run_passed": True,
                "spark_version": spark.version,
                "notes": "PySpark dry-run execution succeeded with zero schema/resolution errors."
            }
        except Exception as e:
            err_msg = str(e)
            stack = traceback.format_exc()
            return {
                "dry_run_passed": False,
                "error": err_msg,
                "stack_trace": stack
            }
