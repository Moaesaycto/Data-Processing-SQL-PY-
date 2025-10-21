#!/usr/bin/python3
# COMP3311 23T3 Ass2 ... track proportion of overseas students

import sys
import psycopg2
import re
from helpers import TERM_LIST

# define any local helper functions here
# ...

### set up some globals

db = None

### process command-line args


try:
  db = psycopg2.connect("dbname=ass2")
  print("Term  #Locl  #Intl Proportion")
  for term in TERM_LIST:
    total_local, total_intl = 0, 0
    cur = db.cursor()
    cur.execute(f"""
      SELECT COUNT(DISTINCT CASE WHEN s.status = 'INTL' THEN s.id END) AS intl_count,
             COUNT(DISTINCT CASE WHEN s.status != 'INTL' THEN s.id END) AS local_count
      FROM Students s
      JOIN Program_enrolments pe ON s.id = pe.student
      JOIN Terms t ON pe.term = t.id
      WHERE t.code = '{term}'
    """)
    intl_count, local_count = cur.fetchone()
    intl_fraction = local_count / intl_count
    print(f"{term} {local_count:6d} {intl_count:6d} {intl_fraction:6.1f}")
    cur.close()

except Exception as err:
  print(err)
finally:
  if db:
    db.close()
