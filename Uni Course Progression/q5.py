#!/usr/bin/python3
# COMP3311 21T3 Ass2 ... progression check for a given student

import sys
import psycopg2
import re
from helpers import getStudent, getProgram, getStream, getStudentProgram, getRequirements, getStudentCourses, generateCourseString, printCourseInfo, printStudentInfo, FAIL_GRADES, UOC_AFFECTING

def getUOCfromCode(db, code):
  cur = db.cursor()
  cur.execute(f"SELECT uoc FROM subjects WHERE code = '{code}'")
  return cur.fetchone()[0]

# define any local helper functions here
def showProgression(requirements, courses, stream):
  # Set up requirements dictionary (as if the student was new)
  reqDict = {
    'streams': [],
    'core': {'components': {}},
    'elective': {"subelectives": {}},
    'gened': { 'courses': [], 'uoc_remaining': 0,},
    'free': { 'courses': [], 'uoc_remaining': 0,},
    'stream_elective': { 'courses': [], 'uoc_remaining': 0,},
  }

  for req in requirements:
    if req[2] == "stream": reqDict['streams'] = req[5].split(',')
    elif req[2] == "core": reqDict['core']['components'][req[1]] = req[5].split(',')
    elif req[1] == stream[1] + " Electives": reqDict['stream_elective']['courses'], reqDict['stream_elective']['uoc_remaining'] = req[5].split(','), req[3]
    elif req[2] == "elective":
      if req[1] not in reqDict['elective']['subelectives'].keys(): reqDict['elective']['subelectives'][req[1]] = {'courses': [], 'uoc_remaining': 0,}
      reqDict['elective']['subelectives'][req[1]]['courses'] += req[5].split(',')
      reqDict['elective']['uoc_remaining'] = req[3]
    elif req[2] == "gened": reqDict['gened']['courses'], reqDict['gened']['uoc_remaining'] = req[5].split(','), req[3]
    elif req[2] == "free": reqDict['free']['courses'], reqDict['free']['uoc_remaining'] = req[5].split(','), req[3]

  courseBelongsDict = {}
  for course in courses:
    if course[4] in FAIL_GRADES or course[4] not in UOC_AFFECTING: continue

    foundCourse = False
    courseCode = course[0].strip("#")

    # Core components
    for compStream in reqDict['core']['components'].keys():
      for i in reqDict['core']['components'][compStream]:
        if courseCode in i: 
          courseBelongsDict[courseCode] = compStream
          reqDict['core']['components'][compStream].remove(i)
          foundCourse = True
    if foundCourse: continue

    # Stream Electives
    if reqDict['stream_elective']['uoc_remaining'] > 0:
      for i in reqDict['stream_elective']['courses']:
        if courseCode in i: 
          courseBelongsDict[courseCode] = stream[1] + " Electives"
          if len(i) != 8: reqDict['stream_elective']['courses'].remove(i)
          reqDict['stream_elective']['uoc_remaining'] -= int(course[5])
          foundCourse = True
      if foundCourse: continue

    # Elective components
    for subelective in reqDict['elective']['subelectives'].keys():
      for i in reqDict['elective']['subelectives'][subelective]['courses']:
        if courseCode in i or (courseCode[:5] in i and len(i.strip("#")) == 5):
          print(courseCode, i, courseCode in i, subelective)
          # print(subelective, courseCode)
          if courseCode in courseBelongsDict.keys(): continue
          courseBelongsDict[courseCode] = subelective
          if len(i) == 8: reqDict['elective']['subelectives'][subelective]['courses'].remove(i)
          reqDict['elective']['subelectives'][subelective]['uoc_remaining'] -= int(course[5])
          foundCourse = True
          break
    if foundCourse: continue

    # GenEd components
    if reqDict['gened']['uoc_remaining'] > 0:
      reqDict['gened']['uoc_remaining'] -= int(course[5])
      courseBelongsDict[courseCode] = "General Education"
      continue

    # Free components
    if reqDict['free']['uoc_remaining'] > 0:
      reqDict['free']['uoc_remaining'] -= int(course[5])
      courseBelongsDict[courseCode] = stream[1] + " Free Electives"
      continue

  printCourseInfo(db, courses, courseBelongsDict)

  canGraduate = True
  for component in reqDict['core']['components'].keys():
    if len(reqDict['core']['components'][component]) != 0:
      remaining = []
      for co in reqDict['core']['components'][component]:
        if '{' in co: remaining.append(co[1:9])
        else: remaining.append(co)
      coursesLeft = sum([getUOCfromCode(db, co) for co in remaining])
      if coursesLeft == 0: continue
      print(f"Need {coursesLeft} more UOC for {component}")
      print(generateCourseString(db, ",".join(reqDict['core']['components'][component]), 'course'))
      canGraduate = False
  
  for subelective in reqDict['elective']['subelectives'].keys():
    if reqDict['elective']['subelectives'][subelective]['uoc_remaining'] > 0:
      canGraduate = False
      for subelective in reqDict['elective']['subelectives'].keys():
        if reqDict['elective']['subelectives'][subelective]['uoc_remaining'] > 0:
          print(f"Need {reqDict['elective']['subelectives'][subelective]['uoc_remaining']} more UOC for {subelective}")
          canGraduate = False

  if reqDict['stream_elective']['uoc_remaining'] > 0:
    print(f"Need {reqDict['stream_elective']['uoc_remaining']} more UOC for {stream[1]} Electives")
    canGraduate = False

  if reqDict['gened']['uoc_remaining'] > 0:
    print(f"Need {reqDict['gened']['uoc_remaining']} more UOC for General Education")
    canGraduate = False
    
  if reqDict['free']['uoc_remaining'] > 0:
    print(f"Need {reqDict['free']['uoc_remaining']} more UOC for {stream[1]} Free Electives")
    canGraduate = False
  
  if canGraduate: print("Eligible to graduate")

### set up some globals

usage = f"Usage: {sys.argv[0]} zID [Program Stream]"
db = None

### process command-line args

argc = len(sys.argv)
if argc < 2:
  print(usage)
  exit(1)
zid = sys.argv[1]
if zid[0] == 'z':
  zid = zid[1:8]
digits = re.compile("^\d{7}$")
if not digits.match(zid):
  print("Invalid student ID")
  exit(1)

progCode = None
strmCode = None

if argc == 4:
  progCode = sys.argv[2]
  strmCode = sys.argv[3]

# manipulate database

try:
  db = psycopg2.connect("dbname=ass2")
  code, psid, requirements = "", "", []

  stuInfo = getStudent(db,zid)
  if not stuInfo:
    print(f"Invalid student id {zid}")
    exit(1)

  if progCode:
    progInfo = getProgram(db,progCode)
    if not progInfo:
      print(f"Invalid program code {progCode}")
      exit(1)
    requirements += getRequirements(db, progInfo, progCode)
    
  if strmCode:
    strmInfo = getStream(db,strmCode)
    if not strmInfo:
      print(f"Invalid program code {strmCode}")
      exit(1)
    requirements += getRequirements(db, strmInfo, strmCode)
  
  # Find it yourself
  if not progCode and not strmCode: 
    pid, sid = getStudentProgram(db,stuInfo[0])[:2]
    strmInfo = getStream(db,sid)
    progInfo = getProgram(db,pid)
    requirements += getRequirements(db, getProgram(db,pid), "*"*4) + getRequirements(db, strmInfo, "*"*6)

  printStudentInfo(db, stuInfo, False, strmInfo, progInfo)
  showProgression(requirements, getStudentCourses(db,stuInfo[0]), strmInfo)

except Exception as err:
  print("DB error: ", err)
finally:
  if db:
    db.close()

