/* Sample Enterprise SAS ETL Program */
DATA work.customer_clean;
    SET work.customer_raw;
    WHERE status = 'ACTIVE' AND age >= 18;
    full_name = UPCASE(STRIP(first_name)) || ' ' || UPCASE(STRIP(last_name));
    signup_year = YEAR(signup_date);
RUN;

PROC SORT DATA=work.customer_clean OUT=work.customer_sorted NODUPKEY;
    BY signup_year DESCENDING age;
RUN;

PROC SQL;
    CREATE TABLE work.yearly_summary AS
    SELECT signup_year, COUNT(*) AS active_users
    FROM work.customer_sorted
    GROUP BY signup_year
    ORDER BY active_users DESC;
QUIT;
