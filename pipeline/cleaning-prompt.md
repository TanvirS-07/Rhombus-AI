   Clean the orders data and keep these columns in this order: order_id, customer_name, email, country, order_date, quantity, amount_usd, status.
   1. Trim spaces at the start and end of every text value and collapse repeated spaces.
   2. Remove exact duplicate rows, then keep only the first row for each order_id.
   3. Convert customer_name to Title Case. If it is empty, set it to "Unknown".
   4. Convert email to lowercase. If it is not a valid email address (for example "N/A"), make it empty.
   5. Convert country to a two-letter ISO code: Australia/AUS -> AU, United States/USA/U.S. -> US, United Kingdom/UK/England/Great Britain -> GB, New Zealand -> NZ, Canada -> CA. If it is empty or unknown, leave it empty.
   6. order_date is in month/day/year format (some rows are already YYYY-MM-DD or like "Jan 14 2025"). Convert all dates to YYYY-MM-DD. Remove rows where the date is empty or not a real date.
   7. Convert quantity to a whole number. Remove rows where quantity is not a number or is zero or negative.
   8. amount_usd is in US dollars. Remove "$" and thousands separators and round to 2 decimal places. Remove rows where it is empty, not a number, or negative.
   9. Convert status to lowercase. Change "canceled" to "cancelled". Any status other than pending, shipped, delivered or cancelled becomes "unknown".