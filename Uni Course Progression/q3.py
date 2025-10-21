#!/usr/bin/python3
# COMP3311 23T3 Ass2 ... print list of rules for a program or stream

import sys
import psycopg2
import re
from helpers import getProgram, getStream, getCourse, getRequirements, generateCourseString

# define any local helper functions here
def minMaxStr(min, max):
  if not min and not max: return ""
  elif min and not max: return f"at least {min}"
  elif not min and max: return f"up to {max}"
  elif min < max: return f"between {min} and {max}"
  else: return f"{min}"

def printRules(info,requirements):
  if not requirements:
    print("No requirements found")
    return
  
  print(f"{info[1]} {info[2]}\nAcademic Requirements:")
  uoc, streamList, coreList, electiveList, gened, free = None, [], [], [], None, None
  for item in requirements:
    if item[2] == "uoc": uoc = item
    elif item[2] == "stream": streamList.append(item)
    elif item[2] == "core": coreList.append(item)
    elif item[2] == "elective": electiveList.append(item)
    elif item[2] == "gened": gened = item
    elif item[2] == "free": free = item
    else: print(f"Invalid requirement {item[2]}")

  # Printing UOC Information
  if uoc: print(f"{uoc[1]} at least {uoc[3]} UOC")

  # Printing Core Information
  for stream in streamList: 
    minMax = minMaxStr(stream[3],stream[4])
    print(f"{minMax} stream{'s' if minMax != '1' else ''} from {stream[1]}\n{generateCourseString(db, stream[5], 'stream')}")
  for core in coreList: print(f"all courses from {core[1]}\n{generateCourseString(db, core[5], 'course')}")
  for elective in electiveList: print(f"{minMaxStr(elective[3], elective[4])} UOC courses from {elective[1]}\n- {elective[5]}")
  for obj in [gened, free]: print(f"{minMaxStr(obj[3], obj[4])} UOC of {obj[1]}") if obj else None



### set up some globals

usage = f"Usage: {sys.argv[0]} (ProgramCode|StreamCode)"
db = None

### process command-line args

argc = len(sys.argv)
if argc < 2:
  print(usage)
  exit(1)
code = sys.argv[1]
if len(code) == 4:
  codeOf = "program"
elif len(code) == 6:
  codeOf = "stream"
else:
  print("Invalid code")
  exit(1)

try:
  db = psycopg2.connect("dbname=ass2")
  if codeOf == "program":
    progInfo = getProgram(db,code)
    if not progInfo:
      print(f"Invalid program code {code}")
      exit(1)
    printRules(progInfo, getRequirements(db,progInfo,code))
    

  elif codeOf == "stream":
    strmInfo = getStream(db,code)
    if not strmInfo:
      print(f"Invalid stream code {code}")
      exit(1)
    printRules(strmInfo, getRequirements(db,strmInfo,code))

except Exception as err:
  print(err)
finally:
  if db:
    db.close()
