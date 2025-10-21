#!/usr/bin/python3
# COMP3311 23T3 Ass2 ... track satisfaction in a given subject

import sys
import psycopg2
import re
from helpers import TERM_LIST

# define any local helper functions here
def getSubject(db, subject):
    results = {}
    for term in TERM_LIST:
        cur = db.cursor()
        cur.execute("""
          SELECT
            c.satisfact AS satisfact,
            c.nresponses AS nresponses,
            COUNT(ce.student) AS num_students,
            COALESCE(p.full_name, '?') AS convenor
          FROM subjects s
          JOIN courses c ON c.subject = s.id
          JOIN Terms t ON c.term = t.id
          LEFT JOIN Course_enrolments ce ON ce.course = c.id
          LEFT JOIN people p ON p.id = c.convenor
          WHERE t.code = %s AND s.code = %s
          GROUP BY c.satisfact, c.nresponses, p.full_name
        """, (term, subject,))

        row = cur.fetchone()
        if row:
            results[term] = {
                "satisfact": str(row[0]) if row[0] is not None else "?",
                "nresponses": str(row[1]) if row[1] is not None else "?",
                "num_students": str(row[2]) if row[2] is not None else "?",
                "convenor": str(row[3]) if row[3] is not None else "?"
            }

    cur.execute("""
      SELECT title FROM subjects WHERE code = %s
    """, (subject,))

    row = cur.fetchone()
    results["title"] = row[0]

    return results

### set up some globals

usage = f"Usage: {sys.argv[0]} SubjectCode"
db = None

### process command-line args

argc = len(sys.argv)
if argc < 2:
  print(usage)
  exit(1)
subject = sys.argv[1]
check = re.compile("^[A-Z]{4}[0-9]{4}$")
if not check.match(subject):
  print("Invalid subject code")
  exit(1)

try:
  db = psycopg2.connect("dbname=ass2")
  subjectInfo = getSubject(db,subject)
  if not subjectInfo:
      print(f"Invalid subject code {code}")
      exit(1)

  print(f"{subject} {subjectInfo['title']}\nTerm  Satis  #resp   #stu  Convenor")
  for key in subjectInfo:
    if key == "title": continue
    currTerm = subjectInfo[key]
    print(f"{key} {currTerm['satisfact']:>6s} {currTerm['nresponses']:>6s} {currTerm['num_students']:>6s}  {currTerm['convenor']}")

except Exception as err:
  print(err)
finally:
  if db:
    db.close()
