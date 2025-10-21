# COMP3311 21T3 Ass2 ... Python helper functions
# add here any functions to share between Python scripts 
# you must submit this even if you add nothing

TERM_LIST = ['19T1', '19T2', '19T3', '20T0', '20T1', '20T2', '20T3', '21T0', '21T1', '21T2', '21T3', '22T0', '22T1', '22T2', '22T3', '23T0', '23T1', '23T2', '23T3']
WAM_AFFECTING = ['HD', 'DN', 'CR', 'PS', 'AF', 'FL', 'UF', 'E', 'F']
UOC_AFFECTING = ['A', 'B', 'C', 'D', 'HD', 'DN', 'CR', 'PS', 'XE', 'T', 'SY', 'EC', 'RC']
FAIL_GRADES = ['AF', 'FL', 'UF', 'E', 'F']

def getProgram(db,code):
  cur = db.cursor()
  cur.execute("select * from Programs where code = %s",[code])
  info = cur.fetchone()
  cur.close()
  if not info:
    return None
  else:
    return info

def getStream(db,code):
  cur = db.cursor()
  cur.execute("select * from Streams where code = %s",[code])
  info = cur.fetchone()
  cur.close()
  if not info:
    return None
  else:
    return info

def getStudent(db,zid):
  cur = db.cursor()
  qry = """
  select p.*
  from   People p
         join Students s on s.id = p.id
  where  p.zid = %s
  """
  cur.execute(qry,[zid])
  info = cur.fetchone()
  cur.close()
  if not info:
    return None
  else:
    return info

def getCourse(db, code):
  cur = db.cursor()
  cur.execute("SELECT title FROM Subjects WHERE code = %s",[code])
  info = cur.fetchone()
  cur.close()
  if not info:
    return None
  else:
    return info

def getRequirements(db,info,code):
  cur = db.cursor()
  if len(code) == 4:
    cur.execute("SELECT * FROM Requirements WHERE for_program = %s", (info[0],))
  else:
    cur.execute("SELECT * FROM Requirements WHERE for_stream = %s", (info[0],))
  info = cur.fetchall()
  cur.close()
  return info if info else None

def getStudentProgram(db, stuId):
  curr = db.cursor()
  curr.execute("""
    SELECT 
      p.code AS code,
      s.code AS stream,
      p.name AS name
    FROM Programs p
    JOIN Program_enrolments pe ON pe.program = p.id
    JOIN Stream_enrolments se ON se.part_of = pe.id
    JOIN Streams s ON se.stream = s.id
    WHERE pe.student = %s
    ORDER BY pe.term DESC
    LIMIT 1
  """, (stuId,))
  info = curr.fetchone()
  curr.close()
  return info if info else None

def getStudentCourses(db, studId):
  curr = db.cursor()
  curr.execute("""
    SELECT
      s.code AS code,
      t.code AS term,
      s.title AS title,
      ce.mark AS mark,
      ce.grade AS grade,
      s.uoc
    FROM Course_enrolments ce
    JOIN Courses c ON ce.course = c.id
    JOIN Subjects s ON c.subject = s.id
    JOIN Terms t ON c.term = t.id
    WHERE ce.student = %s
    ORDER BY t.code, s.code
  """, (studId,))
  info = curr.fetchall()
  curr.close()
  return info if info else None

def generateCourseString(db, listString, listType):
  result = ""
  getTitle = lambda t: getCourse(db,t)[0] if listType == 'course' else getStream(db,t)[2]
  for course in listString.split(','):
    if course[0] == '{' and course[-1] == '}': result += '- ' + '\n  or '.join(f"{co} {getTitle(co)}" for co in course[1:-1].split(';')) + '\n'
    else: result += f"- {course} {getTitle(course)}" + '\n'
  return result[:-1]

def printStudentInfo(db, stuInfo, courseInfo=True, strmCode=None, progCode=None):
  degInfo = getStream(db, strmCode[1]) + getProgram(db, progCode[1]) if strmCode and progCode else getStudentProgram(db, stuInfo[0])
  print(f"{stuInfo[1]} {stuInfo[2]}, {stuInfo[3]}\n{degInfo[4]} {degInfo[1]} {degInfo[2]}")
  stuCourses = getStudentCourses(db, stuInfo[0])
  if courseInfo: printCourseInfo(db, stuCourses)

def printCourseInfo(db, courseInfo, courseBelongsDict=None):
  totalAchievedUoc, totalAttemptedUoc, uocForWam, weightedMarkSum = 0, 0, 0, 0
  for course in courseInfo:
    currUoc, failed = " fail" if course[4] in FAIL_GRADES else ' ' + str(course[5]), course[4] in FAIL_GRADES
    if courseBelongsDict and course[0] not in courseBelongsDict.keys() and not failed: currUoc = ' 0'
    mark = str(course[3]) if course[3] else ' -'
    uocStr = f"{currUoc:2s}{'uoc' if not failed else ''}" if course[4] in UOC_AFFECTING or failed else ("" if not course[4] and not course[3] else " unrs")
    grade = f"{course[4]:>2}" if course[4] else ' -'
    mainString = f"{course[0]} {course[1]} {course[2][:31]:<32s}{mark:>3s} {grade}  {uocStr}"
    if courseBelongsDict:
      mainString += '  ' + courseBelongsDict[course[0]] if course[0] in courseBelongsDict.keys() and not failed else ("  Could not be allocated" if course[3] and not failed else '')
    print(mainString)
    
    if uocStr == ' unrs': continue

    achievedUoc = course[5] if course[4] in UOC_AFFECTING and currUoc != ' 0' else 0
    attemptedUoc = course[5]
    courseMark = course[3] if course[3] else 0
    totalAchievedUoc += achievedUoc
    totalAttemptedUoc += attemptedUoc
    if course[4] in WAM_AFFECTING: uocForWam += attemptedUoc
    weightedMarkSum += courseMark * attemptedUoc
  print(f"UOC = {totalAchievedUoc}, WAM = {round(weightedMarkSum / uocForWam if uocForWam else 0, 1)}")
