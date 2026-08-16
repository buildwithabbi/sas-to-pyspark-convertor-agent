import re
from typing import List, Dict, Any, Tuple


class PySparkOptimizerAgent:
    """Agent 4 - Optimizer: Refactors and optimizes generated PySpark code for performance and efficiency."""

    def optimize_code(self, pyspark_code: str) -> Tuple[str, List[str]]:
        optimizations = []
        code = pyspark_code

        # 1. Detect and warn/remove dangerous .collect() calls
        if ".collect()" in code:
            code = re.sub(r'([a-zA-Z0-9_]+)\.collect\(\)', r'\1.take(100)', code)
            optimizations.append("Replaced unbounded .collect() with .take(100) to prevent Out-Of-Memory (OOM) errors.")

        # 2. Add broadcast hint for lookup tables in joins
        if ".join(" in code and "ratings" in code.lower():
            code = re.sub(r'\.join\(\s*([a-zA-Z0-9_]*ratings[a-zA-Z0-9_]*)', r'.join(F.broadcast(\1)', code)
            optimizations.append("Added F.broadcast() join hint for dimension lookup table.")

        # 3. Clean up redundant .cache() calls
        cache_count = code.count(".cache()")
        if cache_count > 2:
            code = code.replace(".cache()", "")
            optimizations.append("Removed redundant .cache() calls to free Spark memory.")

        # 4. Replace PySpark count() inside loops with aggregation
        if re.search(r'for\s+.*\s+in\s+.*:\s*.*\.count\(\)', code):
            optimizations.append("Suggested replacing Python loop counts with group-by count aggregation.")

        return code, optimizations

    def optimize_steps(self, translated_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        optimized_steps = []
        for step in translated_steps:
            orig_code = step.get("pyspark_code", "")
            opt_code, opts = self.optimize_code(orig_code)
            step_copy = dict(step)
            step_copy["pyspark_code"] = opt_code
            step_copy["optimizations"] = opts
            optimized_steps.append(step_copy)
        return optimized_steps
