import unittest
from backend.services.sql.sql_quality_validator import validate_sql

class TestSQLQualityValidator(unittest.TestCase):

    def test_aggregate_alias_warning(self):
        # Should warn about missing alias for aggregate expression
        query = "SELECT MAX(amount) FROM sales"
        result = validate_sql(query)
        self.assertTrue(result["is_valid"])
        self.assertTrue(any("missing a meaningful alias" in w for w in result["warnings"]))
        
        # Valid alias with nested functions
        query_nested = "SELECT ROUND(MAX(amount), 2) AS max_amount FROM sales"
        result_nested = validate_sql(query_nested)
        self.assertFalse(any("missing a meaningful alias" in w for w in result_nested["warnings"]))

        # Valid alias with CAST
        query_cast = "SELECT CAST(MAX(amount) AS DOUBLE) AS highest FROM sales"
        result_cast = validate_sql(query_cast)
        self.assertFalse(any("missing a meaningful alias" in w for w in result_cast["warnings"]))

    def test_monetary_rounding_warning(self):
        # Should warn about monetary rounding
        query = "SELECT MAX(price) AS max_price FROM sales"
        result = validate_sql(query)
        self.assertTrue(result["is_valid"])
        self.assertTrue(any("automatically round to two decimal places" in w for w in result["warnings"]))

        # Valid rounding
        query_valid = "SELECT ROUND(MAX(price), 2) AS max_price FROM sales"
        result_valid = validate_sql(query_valid)
        self.assertFalse(any("automatically round to two decimal places" in w for w in result_valid["warnings"]))

    def test_group_by_validation(self):
        query = "SELECT category, MAX(price) AS max_price FROM sales"
        result = validate_sql(query)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("Missing GROUP BY when required" in c for c in result["critical_issues"]))

        query_valid = "SELECT category, MAX(price) AS max_price FROM sales GROUP BY category"
        result_valid = validate_sql(query_valid)
        self.assertTrue(result_valid["is_valid"])
        self.assertFalse(any("Missing GROUP BY when required" in c for c in result_valid["critical_issues"]))
        
        query_nested = "SELECT ROUND(MAX(price), 2) AS max_price FROM sales"
        result_nested = validate_sql(query_nested)
        self.assertTrue(result_nested["is_valid"])
        self.assertFalse(any("Missing GROUP BY when required" in c for c in result_nested["critical_issues"]))

    def test_order_by_validation(self):
        query = "SELECT category, SUM(amount) AS total FROM sales GROUP BY category ORDER BY total ASC"
        question = "What is the category with the highest sales?"
        result = validate_sql(query, question=question)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("Incorrect ORDER BY direction: Expected DESC" in c for c in result["critical_issues"]))

        query_valid = "SELECT category, SUM(amount) AS total FROM sales GROUP BY category ORDER BY total DESC LIMIT 1"
        result_valid = validate_sql(query_valid, question=question)
        self.assertTrue(result_valid["is_valid"], result_valid["diagnostics"])
        self.assertFalse(any("Incorrect ORDER BY direction" in c for c in result_valid["critical_issues"]))

    def test_limit_validation(self):
        query = "SELECT category, SUM(amount) AS total FROM sales GROUP BY category ORDER BY total DESC"
        question = "What are the top 5 categories by sales?"
        result = validate_sql(query, question=question)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("Missing LIMIT for Top/Bottom N queries" in c for c in result["critical_issues"]))

        query_valid = "SELECT category, SUM(amount) AS total FROM sales GROUP BY category ORDER BY total DESC LIMIT 5"
        result_valid = validate_sql(query_valid, question=question)
        self.assertTrue(result_valid["is_valid"])
        self.assertFalse(any("Missing LIMIT for Top/Bottom N queries" in c for c in result_valid["critical_issues"]))

    def test_unknown_column_detection(self):
        schema = {
            "columns": [{"name": "id"}, {"name": "amount"}]
        }
        query = 'SELECT "invalid_col", MAX("amount") AS max_amt FROM sales GROUP BY "invalid_col"'
        result = validate_sql(query, schema=schema)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("Invalid column reference" in c for c in result["critical_issues"]))

    def test_select_star_misuse(self):
        query = "SELECT * FROM sales"
        result = validate_sql(query)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("Misuse of SELECT *" in c for c in result["critical_issues"]))

if __name__ == "__main__":
    unittest.main()
