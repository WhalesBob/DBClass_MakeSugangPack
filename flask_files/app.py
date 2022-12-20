# pip install flask, pip install pymysql, pip install cryptography 명령어 필요.(터미널에서 입력하면 다운로드 기능 실행됨)
# 실행방법 : console 창에 python app.py 입력하기
# 이후, localhost 의 port : 5000 에 페이지가 열립니다.

from flask import Flask, render_template, flash, redirect, request
import pymysql

app = Flask(__name__)
app.config.update(
    SECRET_KEY='KnU_SuGANgpAcK_Hw_2015116293'
)

def connectDB():
    db = pymysql.connect( # 자기의 mysql 상황에 맞게 수정가능.
        host = 'localhost',
        port = 3306,
        user = 'forFallSemester',
        passwd='1234',
        db = 'fallsemester_2022',
        charset='utf8'
    )
    return db;

def takeInformation():
    db = connectDB()
    cursor = db.cursor()
        
    student_id = request.form["student_id"]
    class_code = request.form["code"]
    
    return student_id, class_code, cursor, db

@app.route("/")
def main(): 
    return render_template('index.html')

@app.route('/view_bag', methods = ['POST'])
def viewBag():
    if request.method == 'POST' :
        student_id, class_code, db_cursor,db = takeInformation()  
        if(student_id == ''):
            flash("학번을 입력해주세요.")
            return redirect("/")
                
        try:
            checkInt = int(student_id)
        except:
            flash("학번은 정수로만 입력가능합니다.")
            return redirect("/")    
        
        sql = """
        select S.GeneralCourseCode, S.CourseClassNumber,N.CourseName, G.Credit
        from sugangpack S, CourseName N, general_course_info G 
        where S.GeneralCourseCode = N.GeneralCourseCode and N.GeneralCourseCode = G.GeneralCourseCode
        and StudentID = {0};
        """.format(student_id)
        
        db_cursor.execute(sql)
        sugangpack = db_cursor.fetchall()
        totalCredit = calculateAllCredit(sugangpack)
        return render_template('index_with_suganglist.html',sugangpack = sugangpack,totalCredit = totalCredit)
                
@app.route("/add_course", methods = ['GET','POST'])
def addCourse():
    if request.method == 'POST' :
        student_id, class_code, db_cursor,db = takeInformation()
        if(student_id == ''):
            flash("학번을 입력해주세요.")
            return redirect("/")
        
        try:
            checkInt = int(student_id)
        except:
            flash("학번은 정수로만 입력가능합니다.")
            return redirect("/")   
        
        try:
            generalCode, classNum, classType, credit, lectureTime = takeCourseInfo(class_code,db_cursor)
        except:
            flash("올바른 과목코드를 입력해주세요(e.g., CLTR0003-001)")
            return redirect("/")
                
        if(generalCode is None):
            flash("해당 과목은 글로벌SW융합전공의 2학기 강좌로 등록되지 않았습니다.")
            return redirect("/")
        
        haveEnoughCredit, alreadyEnrolled, haveEnoughCultureClass = checkPackInfo(db_cursor,student_id,credit,generalCode,classNum,(classType == '교양'))
        
        if(haveEnoughCredit):
            flash("수강꾸러미에 담은 학점이 24학점을 넘습니다.")
            return redirect("/")
        
        elif(alreadyEnrolled):
            flash("이미 담은 강좌입니다.")
            return redirect("/")
        
        elif(haveEnoughCultureClass):
            flash("신청한 교양수업이 3개를 넘습니다.")
            return redirect("/")
        
        elif(checkAlreadyUseTime(student_id,lectureTime,db_cursor)):
            flash("기존에 신청한 강의와 시간이 겹치는 강의를 선택하셨습니다.")
            return redirect("/")
        
        elif(isOverFlowStudentQuota(db_cursor,generalCode,classNum)):
            flash("수강정원 초과입니다.")
            return redirect("/")
        
        else:
            sql = """INSERT INTO 
            sugangpack(StudentID,GeneralCourseCode,CourseClassNumber) VALUES
            ({0},\'{1}\',{2});""".format(student_id,generalCode,classNum)
            db_cursor.execute(sql)
            db.commit()
            flash("수강꾸러미 담기에 성공했습니다.")
            return redirect("/")
    else :
        return redirect("/")

@app.route("/del_course", methods = ['GET','POST'])
def deleteCourse():
    if request.method == 'POST' :
        student_id, class_code, db_cursor,db = takeInformation()
        if(student_id == ''):
            flash("학번을 입력해주세요.")
            return redirect("/")
        
        try:
            checkInt = int(student_id)
        except:
            flash("학번은 정수로만 입력가능합니다.")
            return redirect("/")   
        
        try:
            generalCode, classCode = class_code.split("-")
            classNum = int(classCode)
        except :     
            flash("올바른 형식의 과목코드를 입력해주세요. (e.g., CLTR0003-005)")
            return redirect("/")
        
        if(isThatPersonNotEnrolled(db_cursor,student_id,generalCode,classNum)):
            flash("아직 담지 않은 강좌는 수강꾸러미에서 삭제할 수 없습니다.")
            return redirect("/")
        
        sql = "delete from sugangpack where GeneralCourseCode = \'{0}\' and CourseClassNumber = {1} and StudentID = {2}".format(generalCode,classNum,student_id)
        db_cursor.execute(sql)
        db.commit()
        flash("해당 과목을 수강꾸러미에서 삭제했습니다.")
        return redirect("/")
    else :
        return redirect("/")
    
def takeCourseInfo(class_code,cursor):
    try:
        generalCode, classInfo = class_code.split("-")
    except:
        raise Exception("올바른 값을 입력해주세요(e.g. CLTR0003-001)")
    
    classNumber = int(classInfo)
    
    sql = "SELECT Type,Credit FROM general_course_info WHERE GeneralCourseCode = \'{0}\'".format(generalCode)
    cursor.execute(sql)
    courseResult = cursor.fetchall()
    if(len(courseResult) == 0):
        return None,None,None,None,None
    
    sql = """SELECT CourseTimeCode, CourseTimeWeek FROM coursetime 
    WHERE GeneralCourseCode = \'{0}\' and CourseClassNumber = {1}""".format(generalCode,classNumber)
    cursor.execute(sql)
    lectureTimeResult = cursor.fetchall()
    
    return generalCode, classNumber, courseResult[0][0], courseResult[0][1], lectureTimeResult;
    

def checkPackInfo(cursor,studentID,lectureCredit,generalCode,classNum,isCulture):
    sql = """
    select S.GeneralCourseCode, S.CourseClassNumber,N.CourseName, G.Credit, G.Type
    from sugangpack S, CourseName N, general_course_info G 
    where S.GeneralCourseCode = N.GeneralCourseCode and N.GeneralCourseCode = G.GeneralCourseCode
    and StudentID = {0}""".format(studentID)
    
    cursor.execute(sql)
    result = cursor.fetchall()
    
    isEnoughCredit = checkPersonsCredit(result,lectureCredit)
    isAlreadyEnrolled = checkAlreadyEnrolled(result,generalCode,classNum)
    haveEnoughCultureClass = checkEnoughCultureClass(result, isCulture)
    
    return isEnoughCredit,isAlreadyEnrolled,haveEnoughCultureClass
    
def checkPersonsCredit(result,lectureCredit):
    creditSum = 0
    for oneLecture in result:
        creditSum += oneLecture[3]
        
    return (creditSum + lectureCredit) > 24

def checkAlreadyEnrolled(result,generalCode,classNum):
    for oneLecture in result:
        if(oneLecture[0] == generalCode and oneLecture[1] == classNum):
            return True
    
    return False;    

def checkEnoughCultureClass(result,isNewClassCulture):
    count = 0
    for oneLecture in result:
        if(oneLecture[4] == '교양'):
            count = count + 1
            
    if(isNewClassCulture):
        count = count + 1
        
    return count > 3     

def checkAlreadyUseTime(studentID,lectureTime,cursor):

    sql = "select CourseTimeCode, CourseTimeWeek from sugangtime where StudentID = {0}".format(studentID)
    cursor.execute(sql)
    alreadyEnrolledTime = cursor.fetchall()
    
    for oneTime in lectureTime:
        if(checkDuplicate(oneTime,alreadyEnrolledTime)):
            return True
    
    return False    
                
def checkDuplicate(oneTime, alreadyEnrolledTime):
    for useTime in alreadyEnrolledTime:
        if(oneTime[0] == useTime[0] and oneTime[1] == useTime[1]):
            return True
    return False      

def calculateAllCredit(sugangpack):
    sum = 0
    for oneLecture in sugangpack:
        sum = sum + oneLecture[3]
        
    return sum      

def isThatPersonNotEnrolled(cursor,studentID,GeneralCourseCode,CourseClassNumber):
    sql = """SELECT * FROM sugangpack 
    WHERE StudentID = {0} and GeneralCourseCode = \'{1}\'
    and CourseClassNumber = {2};""".format(studentID,GeneralCourseCode,CourseClassNumber)
    
    cursor.execute(sql)
    result = cursor.fetchall()
    
    return len(result) == 0

def isOverFlowStudentQuota(cursor,GeneralCourseCode, CourseClassCode):
    sql = """SELECT StudQuota, StudTake FROM course 
    WHERE GeneralCourseCode = \'{0}\' and CourseClassNumber = {1}""".format(GeneralCourseCode,CourseClassCode)
    cursor.execute(sql)
    result = cursor.fetchall()
    
    return (result[0][0] <= result[0][1])
    
if __name__ == "__main__" :
    app.run(host="0.0.0.0", port=5000, debug=False)