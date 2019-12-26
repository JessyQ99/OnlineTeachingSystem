from flask import Flask, redirect, url_for, request, render_template, flash, abort, make_response, session
from flask_uploads import send_from_directory, UploadNotAllowed, UploadSet, DEFAULTS, configure_uploads, ALL
from flask_login import UserMixin, LoginManager, login_required, login_user, logout_user, current_user
from moviepy.editor import VideoFileClip
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from os import remove, path
from flask_wtf import CsrfProtect
from functools import  wraps
import pymysql

#admin部分需要的库函数
import os
import uuid  # 生成唯一字符串
import datetime  # 生成时间
import csv
import io


app = Flask(__name__)
pymysql.install_as_MySQLdb()
basedir = os.path.abspath(os.path.dirname(__file__))

#app.config['SECRET_KEY'] = os.urandom(24)
#manager = Manager(app)

# url的格式为：数据库的协议：//用户名：密码@ip地址：端口号（默认可以不写）/数据库名



my_host='101.132.134.101'
my_user='root'
my_password='123456'
my_db='online_teaching'

app.secret_key = '123456'


app.config["SQLALCHEMY_DATABASE_URI"]= 'mysql+mysqlconnector://root:123456@101.132.134.101:3306/online_teaching'
#app.config["SQLALCHEMY_DATABASE_URI"]=  'sqlite:///' + os.path.join(basedir, 'teachingsystem.db3')+'?check_same_thread=False'

db1 = SQLAlchemy(app,use_native_unicode="utf-8")
db1.metadata.clear()

class Permission: #用户权限控制列表
    SUPERADMINISTRATOR=2
    ADMINISTRATOR = 4#这个权限要异或
    CREATEPERSONPAGE= 8#教师创建修改个人主页
    TEACHERVIEW=16
    STUDENTVIEW=32
    TAVIEW=64
    VIEWHOMEWORK=128

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args,**kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator



class User(UserMixin, db1.Model):
    __tablename__ = 'user'
    __table_args__ = {"useexisting": True}
    name = db1.Column(db1.String(10), primary_key=True,unique=True)
    passwd = db1.Column(db1.String(20))
    type = db1.Column(db1.String(2),db1.ForeignKey('roles.type'))
    ID = db1.Column(db1.Integer)
    gender=db1.Column(db1.String(2))
    age=db1.Column(db1.Integer)
    affiliation=db1.Column(db1.String(20))
    legality=db1.Column(db1.Boolean)

    def __init__(self, name,passwd,type,ID,gender,age,affiliation,legality):
        self.name=name
        self.passwd=passwd
        self.type=type
        self.ID=ID
        self.gender=gender
        self.age=age
        self.affiliation=affiliation
        self.legality=legality
        self.role=Role.query.filter_by(type=self.type).first() #初始化时即绑定角色
    def can(self, permissions): # 这个方法用来传入一个权限来核实用户是否有这个权限,返回bool值
        return (self.role.permissions & permissions) == permissions

    def get_username(self):
        return self.name

    def verify_password(self, password):
        if password == self.passwd:
            return True
        else:
            return False
    def get_id(self):
        return self.name
    def __repr__(self):
        return '<User %r>' % self.name

class Role(db1.Model):
    # 定义Role的数据库模型
    __tablename__ = 'roles'
    type= db1.Column(db1.String, primary_key=True)
    # 该用户角色对应的权限
    permissions = db1.Column(db1.BIGINT)
    description=db1.Column(db1.String)
    users = db1.relationship('User', backref='role', lazy='dynamic')




class ExitingId(db1.Model):
    __tablename__ = 'exitingid'
    id=db1.Column(db1.Integer,primary_key=True,unique=True)
    type=db1.Column(db1.String)
    def __init__(self,id,type):
        self.id=id
        self.type=type
    def getid(self):
        return self.id
    def gettype(self):
        return self.type




class TeacherCV(db1.Model):
    __tablename__ = 'teachercv'
    name=db1.Column(db1.String,db1.ForeignKey('user.name'),primary_key=True)
    u_name=db1.Column(db1.String)
    photourl=db1.Column(db1.String)
    briefinfo=db1.Column(db1.String)
    details=db1.Column(db1.String)
    def __init__(self,name,u_name,photourl,briefinfo,details):
        self.name=name
        self.u_name=u_name
        self.photourl=photourl
        self.briefinfo=briefinfo
        self.details=details
    def getid(self):
        return self.id
    def gettype(self):
        return self.type

class Publication(db1.Model):
    __tablename__='publication'
    a_id=db1.Column(db1.Integer,primary_key=True)
    author=db1.Column(db1.String,db1.ForeignKey('user.name'))
    title=db1.Column(db1.String)
    publication_time=db1.Column(db1.String)
    field=db1.Column(db1.String)
    link=db1.Column(db1.String)
    def __init__(self,a_id,author,title,publication_time,field,link):
        self.a_id=a_id
        self.author=author
        self.title=title
        self.publication_time=publication_time
        self.field=field
        self.link=link


class Course(db1.Model):
    __tablename__='course'
    course_id=db1.Column(db1.Integer,primary_key=True)
    course_name=db1.Column(db1.String)
    course_type=db1.Column(db1.String)
    course_start=db1.Column(db1.Date)
    course_introduction=db1.Column(db1.String)
    course_grading=db1.Column(db1.String)
    course_outline=db1.Column(db1.String)
    course_pre=db1.Column(db1.String)
    def __init__(self,course_id,course_name,course_type,course_start,course_introduction,course_grading,course_outline,course_pre):
        self.course_id=course_id
        self.course_name=course_name
        self.course_type=course_type
        self.course_start=course_start
        self.course_introduction=course_introduction
        self.course_grading=course_grading
        self.course_outline=course_outline
        self.course_pre=course_pre


class Teaching(db1.Model):
    __tablename__='teaching'
    teach_id=db1.Column(db1.Integer,primary_key=True)
    course_id=db1.Column(db1.Integer)
    ID=db1.Column(db1.Integer)
    def __init__(self, teach_id, course_id,ID):
        self.teach_id=teach_id
        self.course_id=course_id
        self.ID=ID



class Message(db1.Model):
    __tablename__='message'
    random_id=db1.Column(db1.Integer,primary_key=True)
    content=db1.Column(db1.String)
    time=db1.Column(db1.String)
    isdeleted=db1.Column(db1.Integer)
    def __init__(self, random_id, content,time,isdeleted):
        self.random_id=random_id
        self.content=content
        self.time=time
        self.isdeleted=isdeleted

class Discussion(db1.Model):
    __tablename__='discussion'
    num=db1.Column(db1.Integer,primary_key=True)
    chapter=db1.Column(db1.Integer)
    cid=db1.Column(db1.Integer)
    uid=db1.Column(db1.Integer,primary_key=True)
    uname=db1.Column(db1.String)
    content=db1.Column(db1.String)
    time=db1.Column(db1.String)
    replyto=db1.Column(db1.Integer)
    isdeleted=db1.Column(db1.Integer)
    def __init__(self,num,chapter,cid,uid,uname,content,time,replyto,isdeleted):
        self.num=num
        self.chapter=chapter
        self.cid=cid
        self.uid=uid
        self.uname=uname
        self.content=content
        self.time=time
        self.replyto=replyto
        self.isdeleted=isdeleted

class Notice(db1.Model):
    __tablename__='notice'
    mid=db1.Column(db1.Integer)
    num=db1.Column(db1.Integer,primary_key=True)
    content=db1.Column(db1.String)
    time=db1.Column(db1.String)
    isdeleted=db1.Column(db1.Integer)
    def __init__(self,num,mid,content,time,isdeleted):
        self.num=num
        self.mid=mid
        self.content=content
        self.time=time
        self.isdeleted=isdeleted

class Cmessage(db1.Model):
    __tablename__='cmessage'
    random_id=db1.Column(db1.Integer,primary_key=True)
    cid=db1.Column(db1.Integer)
    content=db1.Column(db1.String)
    time=db1.Column(db1.String)
    isdeleted=db1.Column(db1.Integer)
    def __init__(self,random_id,cid,content,time,isdeleted):
        self.num=random_id
        self.mid=cid
        self.content=content
        self.time=time
        self.isdeleted=isdeleted




login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = u"请先注册或登录。"
login_manager.session_protection = "strong"
login_manager.remember_cookie_duration = datetime.timedelta(seconds=60)

teacherlist = []
courselist = []
@app.route('/',methods=['GET','POST']) #直接刷新会有问题...
def searchHomePage():
    global  teacherlist
    global  courselist
    if request.method=='POST':
        key_word = request.form.get('searchTeacher')
        course_word=request.form.get('searchCourse')
        teacherlist=[]
        courselist=[]
        if key_word:
            teacherlist= User.query.filter_by(type='T').filter(User.name.like("%" + key_word + "%")).all()
        if course_word:
            courselist=Course.query.filter(Course.course_name.like("%"+course_word+"%")).all()
        return redirect (url_for('searchHomePage'))
    return render_template('user/homepage.html',teachers=teacherlist,courses=courselist)

@app.route('/<u_id>') #直接刷新会有问题...
def backtoHomePage(u_id):
    sql_user = "SELECT * FROM user WHERE ID=%s" % (u_id)

    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()

    cursor.execute(sql_user)
    result_user = cursor.fetchone()

    my_connect.close()
    if result_user[2] == 'T':
        return redirect(url_for('homepage2'))
    elif result_user[2] == 'S':
        return redirect(url_for('homepage1'))
    elif result_user[2] == 'TA':
        return redirect(url_for('homepage3'))
    elif result_user[2] == 'V':
        return redirect(url_for('searchHomePage'))

@login_manager.user_loader
def load_user(name):
    return User.query.get(name)


@app.route('/login', methods=['GET', 'POST'])
def login():
    global teacherlist
    global courselist
    teacherlist = []
    courselist = []
    if request.method=='POST':
        login_name = request.form.get('username', None)
        login_password = request.form.get('password', None)
        login_state=bool(request.form.get('userrememberme'))
        register_name = request.form.get('account', None)
        register_password = request.form.get('upassword', None)
        repeat_password=request.form.get('urepeatpassword',None)
        if  login_name and login_password:
            user = User.query.filter_by(name=login_name, passwd=login_password).first()
            if user is None:
                flash('用户账号或密码错误！',category='err')
                return redirect(url_for('login'))
            elif user.legality is False:
                flash('用户被禁用！', category='err')
                return redirect(url_for('login'))
            else:
                login_user(user,remember=login_state )
                #session['name'] = user.get_username()
                if user.type=='T':
                    return redirect(url_for('homepage2'))
                elif user.type=='S':
                    return redirect(url_for('homepage1'))
                elif user.type=='TA':
                    return redirect(url_for('homepage3'))
                elif user.type=='A':
                    session['login_admin'] = login_name
                    return redirect(url_for('homepage4'))
        elif register_name and register_password:
            ID = request.form.get('id')
            age = request.form.get('age', None)
            gender = request.form.get('gender', None)
            affiliation = request.form.get('aff', None)
            person = ExitingId.query.filter_by(id=ID).first()
            if person is None:
                flash('非本校用户无注册权限！',category='err')
            elif  User.query.filter_by(name=register_name).first():
                flash('已存在对应账号！',category='err')
            elif repeat_password!=register_password:
                flash('两次输入密码不一致！',category='err')
            else:
                type = person.gettype()
                re=User.query.filter_by(name=register_name)
                user = User(name=register_name, passwd=register_password, type=type, ID=ID, age=age, gender=gender,affiliation=affiliation, legality=True)
                db1.session.add(user)
                db1.session.commit()
            return redirect(url_for('login'))
    return render_template('user/sign-up.html')



@app.route('/homepage1',methods=['GET', 'POST'])
@login_required
@permission_required(Permission.STUDENTVIEW)
def homepage1():
    if request.method == 'POST':
        key_word = request.form.get('searchTeacher')
        course_word = request.form.get('searchCourse')
        global teacherlist
        global courselist
        if key_word:
            teacherlist = User.query.filter_by(type='T').filter(User.name.like("%" + key_word + "%")).all()
        if course_word:
            courselist = Course.query.filter(Course.course_name.like("%" + course_word + "%")).all()
        return redirect(url_for('homepage1'))
    return render_template('user/homepage1.html', teachers=teacherlist, courses=courselist)

@app.route('/homepage2',methods=['GET', 'POST'])
@login_required
@permission_required(Permission.TEACHERVIEW)
def homepage2():
    if request.method == 'POST':
        key_word = request.form.get('searchTeacher')
        course_word = request.form.get('searchCourse')
        global teacherlist
        global courselist
        if key_word:
            teacherlist = User.query.filter_by(type='T').filter(User.name.like("%" + key_word + "%")).all()
        if course_word:
            courselist = Course.query.filter(Course.course_name.like("%" + course_word + "%")).all()
        return redirect(url_for('homepage2'))
    return render_template('user/homepage2.html', teachers=teacherlist, courses=courselist)

@app.route('/homepage3',methods=['GET', 'POST'])
@login_required
@permission_required(Permission.TAVIEW)
def homepage3():
    if request.method == 'POST':
        key_word = request.form.get('searchTeacher')
        course_word = request.form.get('searchCourse')
        global teacherlist
        global courselist
        if key_word:
            teacherlist = User.query.filter_by(type='T').filter(User.name.like("%" + key_word + "%")).all()
        if course_word:
            courselist = Course.query.filter(Course.course_name.like("%" + course_word + "%")).all()
        return redirect(url_for('homepage3'))
    return render_template('user/homepage3.html', teachers=teacherlist, courses=courselist)

@app.route('/homepage4',methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ADMINISTRATOR)
def homepage4():
    if request.method == 'POST':
        key_word = request.form.get('searchTeacher')
        course_word = request.form.get('searchCourse')
        global teacherlist
        global courselist
        if key_word:
            teacherlist = User.query.filter_by(type='T').filter(User.name.like("%" + key_word + "%")).all()
        if course_word:
            courselist = Course.query.filter(Course.course_name.like("%" + course_word + "%")).all()
        return redirect(url_for('homepage4'))
    return render_template('user/homepage4.html', teachers=teacherlist, courses=courselist)



@app.route('/logout')
@login_required
def logout():
    logout_user()
    global  teacherlist
    global  courselist
    teacherlist=[]
    courselist=[]
    return redirect(url_for('searchHomePage'))

@app.route('/user')
@login_required
def user_info():
    path1="../static/images/male.jpg"
    path2="../static/images/female.jpg"
    if current_user.gender=='F':
        return render_template('user/user-profile.html',imagepath=path2)
    else:
        return render_template('user/user-profile.html',imagepath=path1)




@app.route('/changepassword',methods=['GET', 'POST'])
@login_required
def changepassword():
    if request.method=='POST':
        oldpwd=request.form.get('oldpassword')
        newpwd=request.form.get('newpassword')
        repeatpwd=request.form.get('repeatpassword')
        if not current_user.verify_password(oldpwd):
            flash("旧密码错误！",category='err')
        elif newpwd!=repeatpwd:
            flash("两次密码不一致！请重新输入",category='err')
        else:
            current_user.passwd=newpwd
            db1.session.add(current_user)
            db1.session.commit()
            flash('提交成功',category='ok')
    return render_template('user/changepassword.html')


@app.route('/editinformation',methods=['GET', 'POST'])
@login_required
def editinformation():
    if request.method=='POST':
        current_user.age=request.form.get('age')
        current_user.gender=request.form.get('gender')
        current_user.affiliation=request.form.get('aff')
        db1.session.add(current_user)
        db1.session.commit()
        flash('修改成功',category='ok')
        return redirect(url_for('editinformation'))
    return render_template('user/editinformation.html')


uploadDir = os.path.join(basedir, 'static\\uploads')#!!!!!!!!!!!!!!
@app.route('/personpage',methods=['GET', 'POST'])
@login_required
@permission_required(Permission.CREATEPERSONPAGE)
def personpage():
    teacherinfo=TeacherCV.query.filter_by(name=current_user.name).first()
    publications=Publication.query.filter_by(author=current_user.name).order_by(Publication.publication_time.desc())
    if not teacherinfo:
        teacherinfo=TeacherCV(name=current_user.name,u_name='Person',photourl="default.jpg",briefinfo="I am...",details="....")
        db1.session.add(teacherinfo)
        db1.session.commit()
    if request.method=='GET':
        if current_user.type!='T':
            abort(403)
    if request.method == 'POST':
        f = request.files.get('selectfile')
        u_name=request.form.get('u_name')
        briefinfo=request.form.get('briefinfo')
        details=request.form.get('details')
        title=request.form.get('title')
        publication_time=request.form.get('time')
        field=request.form.get('field')
        print(field)
        link=request.form.get('link')
        if briefinfo :
            filename = secure_filename(f.filename)
            types = ['jpg', 'png', 'tif']
            if filename.split('.')[-1] in types:
                uploadpath = os.path.join(uploadDir, filename)
                if os.path.exists(uploadpath):
                    newfilename = resolve_conflict(uploadDir, filename) #解决文件冲突问题
                    uploadpath=os.path.join(uploadDir, newfilename)
                uploadpath=uploadpath.replace("\\","/") #chrome只能支持'/'
                f.save(uploadpath)
                teacherinfo.photourl=filename
                flash('照片上传成功!', category='ok')
                db1.session.add(teacherinfo)
            teacherinfo.briefinfo=briefinfo
            teacherinfo.details=details
            teacherinfo.u_name=u_name
            db1.session.add(teacherinfo)
            db1.session.commit()
        elif title and publication_time and field and link:
            article=Publication(a_id=None,author=current_user.name,title=title,publication_time=publication_time,field=field,link=link)
            db1.session.add(article)
            db1.session.commit()

        return redirect(url_for('personpage'))
    return render_template('user/teacher-CV.html',imagename=teacherinfo.photourl,briefinfo=teacherinfo.briefinfo,
                           details=teacherinfo.details,u_name=teacherinfo.u_name,publications=publications)




def resolve_conflict(target_folder,name):
    count = 0
    filename, ext = os.path.splitext(name)
    while True:
        count = count + 1
        newname = '%s_%d%s' % (filename, count, ext)
        if not os.path.exists(os.path.join(target_folder, newname)):
            return newname


@app.route('/teacherintro/<string:teacherName>',methods=['GET', 'POST'])
def teacherintro(teacherName=None): #教师介绍
    teacherinfo=TeacherCV.query.filter_by(name=teacherName).first()
    if teacherinfo:
        publications = Publication.query.filter_by(author=teacherinfo.name).order_by(Publication.publication_time.desc())
    if not teacherinfo:
        abort(404)
    else:
        return render_template('user/teacher-intro.html',imagename=teacherinfo.photourl,briefinfo=teacherinfo.briefinfo,details=teacherinfo.details,u_name=teacherinfo.u_name,publications=publications)


@app.route('/deleteid/<int:deleteid>',methods=['GET', 'POST'])
@login_required
def delete_article(deleteid=None): #删除文章
    article=Publication.query.filter_by(a_id=deleteid).first()
    db1.session.delete(article)
    db1.session.commit()
    return redirect(url_for('personpage'))

@app.route('/returnhome',methods=['GET', 'POST']) #很奇怪，先这么写
@login_required
def returnhome():
    global teacherlist
    global courselist
    teacherlist = []
    courselist = []
    if current_user.type=='T':
        return redirect(url_for('homepage2'))
    elif current_user.type=='S':
        return redirect(url_for('homepage1'))
    elif current_user.type=='TA':
        return  redirect(url_for('homepage3'))
    else:
        return  redirect(url_for('homepage4'))


@app.route('/course_infomation/<c_id><u_id>')
def course_infomation(c_id, u_id):
    sql_course = "SELECT * FROM course WHERE course_id=%s" % (c_id)
    sql_teacher = "SELECT * FROM user NATURAL JOIN teaching WHERE course_id=%s" % (c_id)
    sql_asistant = "SELECT * FROM user NATURAL JOIN asistant WHERE course_id=%s" % (c_id)
    sql_student = "SELECT COUNT(DISTINCT ID) FROM selecting WHERE course_id=%s" % (c_id)
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    cursor.execute(sql_course)
    r_course=cursor.fetchone()
    cursor.execute(sql_teacher)
    r_teacher=cursor.fetchall()
    cursor.execute(sql_asistant)
    r_asistant = cursor.fetchall()
    cursor.execute(sql_student)
    r_student=cursor.fetchone()
    cursor.close()
    my_connect.close()
    return render_template("course_info.html", u= r_course, v=r_teacher, w=r_asistant, x=r_student, y=u_id)

@app.route('/course_manage/<c_id><u_id>')
def course_manage(c_id, u_id):
    sql_user = "SELECT * FROM user WHERE ID=%s" % (u_id)
    sql_teacher = "SELECT * FROM teaching WHERE course_id=%s AND ID=%s" % (c_id, u_id)
    sql_student = "SELECT * FROM selecting WHERE course_id=%s AND ID=%s" % (c_id, u_id)
    sql_asist = "SELECT * FROM asistant WHERE course_id=%s AND ID=%s" % (c_id, u_id)
    sql_course = "SELECT * FROM course WHERE course_id=%s" % (c_id)

    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()

    cursor.execute(sql_user)
    r_user = cursor.fetchone()
    cursor.execute(sql_course)
    r_course = cursor.fetchone()

    if r_user[2] == "T":
        cursor.execute(sql_teacher)
        r_teacher = cursor.fetchone()
        if r_teacher:
            response = make_response(render_template("course_manage.html", u= c_id, v=u_id))
            response.set_cookie('course_id', c_id)
            response.set_cookie('user_id', u_id)
            response.set_cookie('user_type', r_user[2])
            response.set_cookie('course_name', r_course[1])
            response.set_cookie('date', str(r_course[3]))
            return response
    if r_user[2] == "S":
        cursor.execute(sql_student)
        r_student = cursor.fetchone()
        if r_student:
            response = make_response(render_template("stu_course_study.html", u=c_id, v=u_id))
            response.set_cookie('course_id', c_id)
            response.set_cookie('user_id', u_id)
            response.set_cookie('user_type', r_user[2])
            response.set_cookie('course_name', r_course[1])
            response.set_cookie('date', str(r_course[3]))
            return response
    if r_user[2] == "TA":
        cursor.execute(sql_asist)
        r_asist = cursor.fetchone()
        if r_asist:
            response = make_response(render_template("asistant_course_manage.html", u=c_id, v=u_id))
            response.set_cookie('course_id', c_id)
            response.set_cookie('user_id', u_id)
            response.set_cookie('user_type', r_user[2])
            response.set_cookie('course_name', r_course[1])
            response.set_cookie('date', str(r_course[3]))
            return response

    response = make_response(render_template("guest_course_study.html", u=c_id, v=u_id))
    response.set_cookie('course_id', c_id)
    response.set_cookie('user_id', u_id)
    response.set_cookie('user_type', "V")
    response.set_cookie('course_name', r_course[1])
    response.set_cookie('date', str(r_course[3]))
    return response

@app.route('/question_set_tea/<c_id>')
def question_set_tea(c_id):
    result=None
    sql1 = "select * from queset where course_id='%s'"%(c_id)

    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()

    try:
        # 执行sql语句
        my_connect.ping(reconnect=True)
        cursor.execute(sql1)
        my_connect.commit()
        # 执行sql语句
        result = cursor.fetchall()
        print(result)
    except:
        # 发生错误时回滚
        my_connect.rollback()

    return render_template('question_set_list.html', queset=result,course_id=c_id)


@app.route('/course_homework/<c_id><t_id>')
def course_homework(c_id, t_id):
    sql_course = "SELECT * FROM course WHERE course_id=%s" % (c_id)
    sql_teacher = "SELECT * FROM user WHERE ID=%s" % (c_id)

    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()

    cursor.execute(sql_course)
    r_course = cursor.fetchone()
    cursor.execute(sql_teacher)
    r_teacher = cursor.fetchone()


    cursor.close()
    my_connect.close()

    return render_template("course_manage.html", u= c_id, v=t_id)

@app.route('/course_set_info/<c_id><t_id>')
def course_set_info(c_id, t_id):
    sql_course = "SELECT * FROM course WHERE course_id=%s" % (c_id)

    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()

    cursor.execute(sql_course)
    r_course=cursor.fetchone()
    cursor.close()
    my_connect.close()

    return render_template("course_set_info.html", u=r_course, v=t_id)

@app.route('/course_set_asistant/<c_id><t_id>')
def course_set_asistant(c_id, t_id):
    sql_asistant = "SELECT * FROM user NATURAL JOIN asistant WHERE course_id=%s" % (c_id)

    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()

    cursor.execute(sql_asistant)
    r_asistant = cursor.fetchall()
    cursor.close()
    my_connect.close()

    return render_template("course_set_asistant.html", u=r_asistant, v=c_id, w=t_id)

@app.route('/course_set_teacher/<c_id><t_id>')
def course_set_teacher(c_id, t_id):
    sql_teacher = "SELECT * FROM user NATURAL JOIN teaching WHERE course_id=%s" % (c_id)

    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()

    cursor.execute(sql_teacher)
    r_teacher = cursor.fetchall()
    print(r_teacher)
    cursor.close()
    my_connect.close()

    return render_template("course_set_teacher.html", u=r_teacher, v=c_id, w=t_id)

@app.route('/course_set_student/<c_id><t_id>')
def course_set_student(c_id, t_id):
    sql_student = "SELECT * FROM user NATURAL JOIN selecting WHERE course_id=%s" % (c_id)

    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()

    cursor.execute(sql_student)
    r_student = cursor.fetchall()
    cursor.close()
    my_connect.close()

    return render_template("course_set_student.html", u=r_student, v=c_id, w=t_id)

@app.route('/course_set_group/<c_id><t_id>')
def course_set_group(c_id, t_id):
    sql_group = "SELECT * FROM grouping NATURAL JOIN user WHERE course_id=%s ORDER BY group_id ASC" % (c_id)

    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()

    cursor.execute(sql_group)
    r_group = cursor.fetchall()

    cursor.close()
    my_connect.close()

    return render_template("course_set_group.html", u=r_group, v=c_id, w=t_id)

@app.route('/random_group/<c_id><t_id>', methods=["GET","POST"])
def random_group(c_id, t_id):
    if request.method == "POST":
        max_number = request.form["group_max"]

        sql_number = "SELECT COUNT(DISTINCT ID) FROM selecting WHERE course_id=%s" % (c_id)

        my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
        cursor = my_connect.cursor()

        cursor.execute(sql_number)
        r_student = cursor.fetchone()

        total_group = int(r_student[0]) / int(max_number)
        term = int(r_student[0]) % int(max_number)

        if term != 0:
            total_group = int(total_group + 1)

        sql_student = "SELECT DISTINCT ID FROM selecting WHERE course_id=%s" % (c_id)

        cursor.execute(sql_student)
        r_student = cursor.fetchall()

        sql_setgroup = 'INSERT INTO grouping (course_id, group_id, ID) VALUES (%s, %s, %s)'
        for i in range(len(r_student)):
            temp = (i % total_group) + 1
            cursor.execute(sql_setgroup, (c_id, temp, r_student[i][0]))
            my_connect.commit()

        sql_course = "SELECT * FROM course WHERE course_id=%s" % (c_id)
        sql_teacher = "SELECT * FROM user NATURAL JOIN teaching WHERE course_id=%s" % (c_id)
        sql_asistant = "SELECT * FROM user NATURAL JOIN asistant WHERE course_id=%s" % (c_id)
        sql_student = "SELECT COUNT(DISTINCT ID) FROM selecting WHERE course_id=%s" % (c_id)

        cursor.execute(sql_course)
        r_course = cursor.fetchone()
        cursor.execute(sql_teacher)
        r_teacher = cursor.fetchall()
        cursor.execute(sql_asistant)
        r_asistant = cursor.fetchall()
        cursor.execute(sql_student)
        r_student = cursor.fetchone()

        cursor.close()
        my_connect.close()

        return render_template("course_info.html", u=r_course, v=r_teacher, w=r_asistant, x=r_student, y=t_id)

@app.route('/course_setinfo_result/<c_id><t_id>',methods=["GET","POST"])
def course_setinfo_result(c_id, t_id):
    if request.method == "POST":
        c_name = request.form["name"]
        c_type = request.form["type"]
        c_introduction = request.form["introduction"]
        c_outline = request.form["outline"]
        c_grading = request.form["grading"]
        c_pre = request.form["pre"]

        sql_setname='UPDATE course SET course_name = "%s" WHERE course_id = %s' % (c_name, c_id)
        sql_settype='UPDATE course SET course_type = "%s" WHERE course_id = %s' % (c_type, c_id)
        sql_setintro = 'UPDATE course SET course_introduction = "%s" WHERE course_id = %s' % (c_introduction, c_id)
        sql_setoutline = 'UPDATE course SET course_outline = "%s" WHERE course_id = %s' % (c_outline, c_id)
        sql_setgrading = 'UPDATE course SET course_grading = "%s" WHERE course_id = %s' % (c_grading, c_id)
        sql_setpre = 'UPDATE course SET course_pre = "%s" WHERE course_id = %s' % (c_pre, c_id)

        my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
        cursor = my_connect.cursor()

        if c_name != "":
            cursor.execute(sql_setname)
            my_connect.commit()
        if c_type != "":
            cursor.execute(sql_settype)
            my_connect.commit()
        if c_introduction != "":
            cursor.execute(sql_setintro)
            my_connect.commit()
        if c_outline != "":
            cursor.execute(sql_setoutline)
            my_connect.commit()
        if c_grading != "":
            cursor.execute(sql_setgrading)
            my_connect.commit()
        if c_pre != "":
            cursor.execute(sql_setpre)
            my_connect.commit()

        sql_course = "SELECT * FROM course WHERE course_id=%s" % (c_id)

        cursor.execute(sql_course)
        r_course = cursor.fetchone()
        cursor.close()
        my_connect.close()

        return render_template("course_set_info.html", u=r_course, v=t_id)

@app.route('/course_setasistant_result/<c_id><t_id>',methods=["GET","POST"])
def course_setasistant_result(c_id, t_id):
    if request.method == "POST":
        a_name = request.form["add_name"]
        d_name = request.form["delete_name"]

        name_select1="SELECT * FROM user WHERE name='%s'" % (a_name)
        name_select2="SELECT * FROM user WHERE name='%s'" % (d_name)


        my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
        cursor = my_connect.cursor()

        if a_name!="":
            cursor.execute(name_select1)
            a_result1 = cursor.fetchone()
            if a_result1:
                sql_setasistant = 'INSERT INTO asistant (course_id, ID) VALUES (%s, %s)'
                cursor.execute(sql_setasistant,(c_id, a_result1[3]))
                my_connect.commit()

        if d_name!="":
            cursor.execute(name_select2)
            a_result2 = cursor.fetchone()
            if a_result2:
                sql_delete = 'DELETE FROM asistant WHERE ID = %s' % (a_result2[3])
                cursor.execute(sql_delete)
                my_connect.commit()

        sql_asistant = "SELECT * FROM user NATURAL JOIN asistant WHERE course_id=%s" % (c_id)

        cursor.execute(sql_asistant)
        r_asistant = cursor.fetchall()
        cursor.close()
        my_connect.close()

        return render_template("course_set_asistant.html", u=r_asistant, v=c_id, w=t_id)

@app.route('/course_setteacher_result/<c_id><t_id>',methods=["GET","POST"])
def course_setteacher_result(c_id, t_id):
    if request.method == "POST":
        a_name = request.form["add_name"]
        d_name = request.form["delete_name"]

        name_select1="SELECT * FROM user WHERE name='%s'" % (a_name)
        name_select2="SELECT * FROM user WHERE name='%s'" % (d_name)


        my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
        cursor = my_connect.cursor()

        if a_name!="":
            cursor.execute(name_select1)
            t_result1 = cursor.fetchone()
            if t_result1:
                sql_setteacher = 'INSERT INTO teaching (course_id, ID) VALUES (%s, %s)'
                cursor.execute(sql_setteacher,(c_id, t_result1[3]))
                my_connect.commit()

        if d_name!="":
            cursor.execute(name_select2)
            t_result2 = cursor.fetchone()
            if t_result2:
                sql_delete = 'DELETE FROM teaching WHERE ID = %s' % (t_result2[3])
                cursor.execute(sql_delete)
                my_connect.commit()

        sql_teacher = "SELECT * FROM user NATURAL JOIN teaching WHERE course_id=%s" % (c_id)

        cursor.execute(sql_teacher)
        r_teacher = cursor.fetchall()
        cursor.close()
        my_connect.close()

        return render_template("course_set_teacher.html", u=r_teacher, v=c_id, w=t_id)

@app.route('/course_setstudent_result/<c_id><t_id>',methods=["GET","POST"])
def course_setstudent_result(c_id, t_id):
    if request.method == "POST":
        a_name = request.form["add_name"]
        d_name = request.form["delete_name"]

        name_select1="SELECT * FROM user WHERE name='%s'" % (a_name)
        name_select2="SELECT * FROM user WHERE name='%s'" % (d_name)

        my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
        cursor = my_connect.cursor()

        if a_name!="":
            cursor.execute(name_select1)
            s_result1 = cursor.fetchone()
            if s_result1:
                sql_setstudent = 'INSERT INTO selecting (course_id, ID) VALUES (%s, %s)'
                cursor.execute(sql_setstudent,(c_id, s_result1[3]))
                my_connect.commit()

        if d_name!="":
            cursor.execute(name_select2)
            s_result2 = cursor.fetchone()
            if s_result2:
                sql_delete = 'DELETE FROM selecting WHERE ID = %s' % (s_result2[3])
                cursor.execute(sql_delete)
                my_connect.commit()

        sql_student = "SELECT * FROM user NATURAL JOIN selecting WHERE course_id=%s" % (c_id)

        cursor.execute(sql_student)
        r_student = cursor.fetchall()
        cursor.close()
        my_connect.close()

        return render_template("course_set_student.html", u=r_student, v=c_id, w=t_id)

@app.route('/course_setgroup_result/<c_id><t_id>',methods=["GET","POST"])
def course_setgroup_result(c_id, t_id):
    if request.method == "POST":
        a_name = request.form["add_name"]
        a_number = request.form["add_number"]
        d_name = request.form["delete_name"]
        d_number = request.form["delete_number"]

        name_select1="SELECT * FROM user WHERE name='%s'" % (a_name)
        name_select2="SELECT * FROM user WHERE name='%s'" % (d_name)

        my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
        cursor = my_connect.cursor()

        if a_name!="":
            if a_number!="":
                cursor.execute(name_select1)
                g_result1 = cursor.fetchone()
                if g_result1:
                    sql_setgroup = 'INSERT INTO grouping (course_id,group_id,ID) VALUES (%s, %s, %s)'
                    cursor.execute(sql_setgroup, (c_id,a_number ,g_result1[3]))
                    my_connect.commit()

        if d_name!="":
            cursor.execute(name_select2)
            g_result2 = cursor.fetchone()
            if g_result2:
                sql_delete = 'DELETE FROM grouping WHERE ID = %s AND course_id = %s AND group_id = %s' % (g_result2[3], c_id, d_number)
                cursor.execute(sql_delete)
                my_connect.commit()

        sql_group = "SELECT * FROM grouping NATURAL JOIN user WHERE course_id=%s ORDER BY group_id ASC" % (c_id)

        cursor.execute(sql_group)
        r_group = cursor.fetchall()

        cursor.close()
        my_connect.close()

        return render_template("course_set_group.html", u=r_group, v=c_id, w=t_id)

@app.route('/course_table/<u_id>')
def course_table(u_id):
    sql_user = "SELECT * FROM user WHERE ID=%s" % (u_id)

    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()

    cursor.execute(sql_user)
    result_user = cursor.fetchone()
    if result_user[2] == 'T':
        sql_select1 = "SELECT * FROM course NATURAL JOIN teaching WHERE ID=%s" % (u_id)

        cursor.execute(sql_select1)
        result_course = cursor.fetchall()
        result_teacher = result_user[0]
        print(result_course)
        print(result_teacher)
        cursor.close()
        my_connect.close()
        return render_template("course_table.html", u=result_course, v=result_teacher, user_id = u_id )
    if result_user[2] == 'S':
        sql_select1 = "SELECT * FROM course NATURAL JOIN selecting WHERE ID=%s" % (u_id)

        cursor.execute(sql_select1)
        result_course = cursor.fetchall()
        result_teacher = ''

        cursor.close()
        my_connect.close()
        return render_template("course_table.html", u=result_course, v=result_teacher, user_id = u_id )
    if result_user[2] == 'TA':
        sql_select1 = "SELECT * FROM course NATURAL JOIN asistant WHERE ID=%s" % (u_id)

        cursor.execute(sql_select1)
        result_course = cursor.fetchall()
        result_teacher = ''

        cursor.close()
        my_connect.close()
        return render_template("course_table.html", u=result_course, v=result_teacher, user_id = u_id )
    if result_user[2] == 'V':
        result_course=()
        result_teacher = ''

        cursor.close()
        my_connect.close()
        return render_template("course_table.html", u=result_course, v=result_teacher, user_id = u_id )

@app.route('/course_build/<c_id><t_id>')
def course_build(c_id,t_id):
    return render_template("course_build.html", course_id=c_id, teacher_id = t_id)


@app.route('/course_result/<t_id>', methods=["GET","POST"])
def course_result(t_id):
    if request.method == "POST":
        c_name = request.form["name"]
        c_type = request.form["type"]
        c_introduction = request.form["introduction"]
        c_outline = request.form["outline"]
        c_grading = request.form["grading"]
        c_pre = request.form["pre"]

        sql_insert1 = 'INSERT INTO course (course_name, course_type, course_start, course_introduction, course_outline, course_grading, course_pre) VALUES (%s, %s, %s, %s, %s, %s, %s)'
        sql_insert2 = 'INSERT INTO teaching (course_id, ID) VALUES (%s, %s)'
        sql_select1 = "SELECT * FROM course WHERE course_name='%s'" % (c_name)
        sql_select2 = "SELECT * FROM course NATURAL JOIN teaching WHERE ID=%s" % (t_id)
        sql_select3 = "SELECT * FROM user WHERE ID=%s" % (t_id)
        my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
        cursor = my_connect.cursor()

        cursor.execute(sql_insert1, (c_name, c_type, datetime.datetime.now().strftime("%Y%m%d%H%M%S"), c_introduction, c_outline, c_grading, c_pre))
        my_connect.commit()

        cursor.execute(sql_select1)
        result1 = cursor.fetchone()
        c_id = int(result1[0])
        cursor.execute(sql_insert2, (c_id, t_id))
        my_connect.commit()

        cursor.execute(sql_select2)
        result_course = cursor.fetchall()

        cursor.execute(sql_select3)
        result3 = cursor.fetchone()
        result_teacher = result3[1]

        cursor.close()
        my_connect.close()
        return render_template("course_table.html", u = result_course, v = result_teacher, user_id = t_id)

@app.route('/course_search/<u_id>',methods=["GET","POST"])
def course_search(u_id):
    if request.method == "POST":
        s_name = request.form["search_course"]

        sql_search = "SELECT * FROM course WHERE course_name REGEXP '%s'" % (s_name)

        my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
        cursor = my_connect.cursor()
        cursor.execute(sql_search)
        result = cursor.fetchall()

        cursor.close()
        my_connect.close()
        return render_template("homepage.html", u=result, v=u_id)

@app.route('/question')
def question():
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    ques=None
    queset = None
    blank=0
    queset_id=request.args.get('queset_id')
    course_id=request.args.get('course_id')
    sql1 = "select * from question where queset_id='%s'" % (queset_id)
    sql2 = "select * from queset where id='%s'" % (queset_id)
    try:
        # 执行sql语句
        my_connect.ping(reconnect=True)
        cursor.execute(sql1)
        ques = cursor.fetchall()

        cursor.execute(sql2)

        queset = [dict(title=row[3], info=row[4],begin=row[5], end=row[6], proportion=row[7])
                   for row in cursor.fetchall()]
        for row in queset:
            blank=1
        my_connect.commit()

        # 执行sql语句


    except:
        # 发生错误时回滚
        my_connect.rollback()

    return render_template('homework_tea.html', question=ques, queset=queset,blank=blank,queset_id=queset_id,course_id=course_id)


@app.route('/questionModify')
def question_modify():
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    blank = request.args.get('blank')
    queset_id = request.args.get('queset_id')
    course_id = request.args.get('course_id')
    title = request.args.get('title')

    if blank == '0':
        if len(title) == 0:
            flash('作业集标题未填写')
            return redirect(request.referrer)

    if(title==None):title=request.args.get('oldtitle')

    begin = request.args.get('begin')
    end = request.args.get('end')
    if blank=='0':
        if begin=='':
            flash('作业集开始时间未填写')
            return redirect(request.referrer)
    if blank=='0':
        if end=='':
            flash('作业集结束时间未填写')
            return redirect(request.referrer)
    if(begin==''): begin=request.args.get('oldbegin')
    if(end ==''): end = request.args.get('oldend')

    proportion = request.args.get('proportion')
    if blank=='0':
        if proportion=='':
            flash('作业集分值未填写')
            return redirect(request.referrer)
    if (proportion == ''): proportion = request.args.get('oldpro')
    info = request.args.get('info')

    sql = "select id from queset"
    sql2 = "update queset set title='%s',start_time='%s', end_time='%s', info='%s',proportion='%s' where id='%s'" % \
           (title, begin, end, info, proportion, queset_id)
    sql3 = "select * from queset where course_id='%s'" % (course_id)
   # 执行sql语句
    my_connect.ping(reconnect=True)

    cursor.execute(sql)
    number = cursor.fetchall()
    for num in number:
        nu=num[0]

    sql1 = "insert into queset (id,course_id,title,start_time, end_time, info,proportion)values('%s','%s','%s','%s','%s','%s','%s')" % \
           (nu+1, 1, title, begin, end, info, proportion)

    if(blank=='1'):
      print(sql2)
      cursor.execute(sql2)
    else:
     print(sql1)
     cursor.execute(sql1)


    cursor.execute(sql3)
    my_connect.commit()
    result = cursor.fetchall()
    print(result)
    return render_template("/question_set_list.html", queset = result, course_id = course_id)

@app.route('/queslib_in/<course_id><t_id>')
def queslib_in(course_id, t_id):
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    sql1 = "select * from queslib where course_id='%s'" % (course_id)
    print(sql1)

    # 执行sql语句
    my_connect.ping(reconnect=True)
    cursor.execute(sql1)
    my_connect.commit()
    # 执行sql语句
    result = cursor.fetchall()
    print(result)

    my_connect.commit()

    queset_id = ""

    return render_template('queslib_in.html', queslib=result, queset_id=queset_id,course_id=course_id,t_id = t_id)


@app.route('/queslib')
def queslib():
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    queset_id = request.args.get('queset_id')
    course_id = request.args.get('course_id')
    sql1 = "select * from queslib where course_id='%s'" % (course_id)
    print(sql1)

    # 执行sql语句
    my_connect.ping(reconnect=True)
    cursor.execute(sql1)
    my_connect.commit()
    # 执行sql语句
    result = cursor.fetchall()
    print(result)

    my_connect.commit()

    return render_template('queslib.html', queslib=result, queset_id=queset_id,course_id=course_id)

@app.route('/add_que')
def add_que():
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    queset_id=request.args.get('queset_id')
    course_id=request.args.get('course_id')
    queslib_id = request.args.get('queslib_id')
    sql1 = "select * from question where queset_id='%s'" % (queset_id)
    sql2 = "select * from queset where id='%s'" % (queset_id)
    sql3="select id from question"
    sql4="select * from queslib where id='%s'"%(queslib_id)

    my_connect.ping(reconnect=True)
    cursor.execute(sql3)
    number = cursor.fetchall()
    for num in number:
        nu = num[0]

    cursor.execute(sql4)
    questionn = cursor.fetchall()
    for question in questionn:
        sql = "insert into question (id,queset_id,type,content,answer,points) values('%s','%s','%s','%s','%s','%s')" % (
            nu + 1, queset_id, question[1], question[2], question[3], question[4])
    print(sql)
    cursor.execute(sql)

    cursor.execute(sql1)
    ques = cursor.fetchall()

    cursor.execute(sql2)
    queset = [dict(title=row[3], info=row[4],begin=row[5], end=row[6], proportion=row[7])
                   for row in cursor.fetchall()]


    my_connect.commit()
    return redirect(request.referrer)
    #return render_template('homework_tea.html', question=ques, queset=queset,blank=1,queset_id=queset_id,course_id=course_id)

@app.route('/add_queslib')
def add_queslib():
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    course_id=request.args.get('course_id')
    type = request.args.get('type')
    if type==None:
        flash('题目类型未选择')
        return redirect(request.referrer)
    type=int(type)
    points = request.args.get('points')
    if points==None:
        flash('分数未填写')
        return redirect(request.referrer)
    content = request.args.get('content')
    if content==None:
        flash('题目内容未填写')
        return redirect(request.referrer)
    answer = request.args.get('answer')
    if answer==None:
        flash('题目答案未填写')
        return redirect(request.referrer)

    sql1 = "select id from queslib"

    my_connect.ping(reconnect=True)
    cursor.execute(sql1)
    number = cursor.fetchall()
    for num in number:
        nu = num[0]
    sql2="insert into queslib (id,type,content,answer,points,course_id) values ('%s','%s','%s','%s','%s','%s')"%(nu+1,type,content,answer,points,course_id)
    cursor.execute(sql2)
    my_connect.commit()
    return redirect(request.referrer)


@app.route('/delete_que')
def delete_que():
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    queset_id = request.args.get('queset_id')
    question_id = request.args.get('question_id')

    sql1 = "delete from question where queset_id='%s' and id='%s'"%(queset_id,question_id)
    print(sql1)

        # 执行sql语句
    my_connect.ping(reconnect=True)
    cursor.execute(sql1)
    my_connect.commit()
        # 执行sql语句
    result = cursor.fetchall()
    print(result)

    queset_id = request.args.get('queset_id')
    course_id = request.args.get('course_id')
    sql1 = "select * from question where queset_id='%s'" % (queset_id)
    sql2 = "select * from queset where id='%s'" % (queset_id)

        # 执行sql语句
    my_connect.ping(reconnect=True)
    cursor.execute(sql1)
    ques = cursor.fetchall()

    cursor.execute(sql2)

    queset = [dict(title=row[3], info=row[4], begin=row[5], end=row[6], proportion=row[7])
                  for row in cursor.fetchall()]
    for row in queset:
         blank = 1
    my_connect.commit()

    return render_template('homework_tea.html', question=ques, queset=queset, blank=blank, queset_id=queset_id,
                           course_id=course_id)


@app.route('/answer_set_tea/<c_id>')
def answer_set_tea(c_id):
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    result = None
    sql1 = "select * from queset where course_id='%s'" % (c_id)
    try:
        # 执行sql语句
        my_connect.ping(reconnect=True)
        cursor.execute(sql1)
        my_connect.commit()
        # 执行sql语句
        result = cursor.fetchall()
        print(result)
    except:
        # 发生错误时回滚
        my_connect.rollback()

    return render_template('answer_set_list.html', queset=result,course_id=c_id)

@app.route('/answer_set_correct')
def answer_set_correct():
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    result = None
    queset_id = request.args.get('queset_id')
    course_id = request.args.get('course_id')
    sql1 = "select * from answerset where queset_id='%s'" % (queset_id)
    try:
        # 执行sql语句
        my_connect.ping(reconnect=True)
        cursor.execute(sql1)
        my_connect.commit()
        # 执行sql语句
        result = cursor.fetchall()
        print(result)
    except:
        # 发生错误时回滚
        my_connect.rollback()

    return render_template('answer_set_correct.html', answerset=result,queset_id=queset_id,u=course_id)

@app.route('/answer')
def answer():
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    ques_content = []
    answer_content = []
    points=[]
    queset_id = request.args.get('queset_id')
    answerset_id = request.args.get('answerset_id')
    sql1 = "select * from answer where answerset_id='%s'" % (answerset_id)
    sql="select * from answerset where id='%s'" %(answerset_id)
    try:
        # 执行sql语句
        my_connect.ping(reconnect=True)
        cursor.execute(sql)
        values = cursor.fetchall()
        for v in values:
            value=v[5]
        if value==None:
            cursor.execute(sql1)
            result = cursor.fetchall()
            for row in result:
                question_id=row[1]
                sql2="select * from question where id='%s'"%(question_id)
                cursor.execute(sql2)
                answer_result = cursor.fetchall()
                for answer in answer_result:
                    if answer[3]==1 :
                        ques_content.append(answer[4])
                        answer_content.append(row[2])
                        points.append(answer[6])

                    elif answer[3] == 3:
                        ques_content.append(answer[4])
                        answer_content.append(row[2])
                        points.append(answer[6])

                    elif answer[3]==0:
                        if(row[2]==answer[5]):
                            point=answer[6]
                            sql3 = "update answer set points='%s',state='2' where question_id='%s'" % (
                            point, question_id)
                        else:
                            point=0
                            sql3 = "update answer set points='%s',state='3' where question_id='%s'" % (
                            point, question_id)
                        cursor.execute(sql3)
                    elif answer[3]==2:
                        if(row[2]==answer[5]):
                            point=answer[6]
                            sql3 = "update answer set points='%s',state='2'where question_id='%s'" % (
                            point, question_id)
                        else:
                            point=0
                            sql3 = "update answer set points='%s',state='3'where question_id='%s'" % (
                            point, question_id)
                        cursor.execute(sql3)
        else: return render_template('answer_value.html',answerset_id=answerset_id,queset_id=queset_id)
        my_connect.commit()
    except:
        # 发生错误时回滚
        my_connect.rollback()

    return render_template('answer_tea.html',queset_id=queset_id,answerset_id=answerset_id,ques_content=ques_content,answer_content=answer_content,len=len(ques_content),points=points)

@app.route('/correct')
def correct():
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    answerset_id = request.args.get('answerset_id')
    queset_id = request.args.get('queset_id')
    point=0
    sql1 = "select * from answerset where queset_id='%s'" % (queset_id)
    my_connect.ping(reconnect=True)
    cursor.execute(sql1)
    result = cursor.fetchall()

    sql4 = "select question_id from answer where answerset_id='%s'and points is null " % (answerset_id)
    cursor.execute(sql4)
    question=cursor.fetchall()
    nu=cursor.rowcount
    print(nu)
    for i in range(0,nu):
        p="%s"%(i)
        points = request.args.get(p)
        if points=='':
            flash('有题目未评分')
            return redirect(request.referrer)
        sql2="update answer set points='%s',state='2' where question_id='%s'"%(points,question[i][0])
        print(sql2)
        cursor.execute(sql2)

    sql5="select * from answer"
    cursor.execute(sql5)
    pp = cursor.fetchall()
    for ppp in pp:
        point=point+ppp[3]

    sql3="update answerset set correct_time='%s',points='%s' where id='%s'"%(datetime.datetime.now(),point,answerset_id)
    cursor.execute(sql3)

    my_connect.commit()
    return render_template('answer_set_correct.html', answerset=result,queset_id=queset_id)

@app.route('/answer_value')
def answer_evaluate():
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    answerset_id = request.args.get('answerset_id')
    queset_id = request.args.get('queset_id')
    value = request.args.get('value')

    sql1 = "select * from answerset where queset_id='%s'" % (queset_id)
    my_connect.ping(reconnect=True)
    cursor.execute(sql1)
    result = cursor.fetchall()

    sql2 = "update answerset set evaluate_time='%s',evaluate='%s' where id='%s'" % (
    datetime.datetime.now(), value,answerset_id)
    cursor.execute(sql2)

    my_connect.commit()
    return render_template('answer_set_correct.html',answerset=result,queset_id=queset_id)

@app.route('/grade')
def grade():
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    course_id = request.args.get('course_id')
    queset_id = request.args.get('queset_id')
    sql1 = "select * from answerset where queset_id='%s'" % (queset_id)
    my_connect.ping(reconnect=True)
    cursor.execute(sql1)
    answerset = cursor.fetchall()
    my_connect.commit()
    return render_template('grade.html',answerset=answerset,course_id=course_id)


VIDEOS = tuple('mp4 webm ogg '.split())
MOVIES = tuple('avi flv wmv'.split())
PDF = tuple('pdf'.split())

app.config['UPLOADED_FILES_ALLOW'] = VIDEOS + PDF + DEFAULTS + MOVIES
files = UploadSet('FILES')

db = pymysql.connect(my_host, my_user, my_password, my_db)
cursor = db.cursor()

dir = os.getcwd()+"/static/sources"


@app.route('/sources', methods=['GET', 'POST'])
def upload_file():
    course_id = request.cookies.get('course_id')
    user_id = request.cookies.get('user_id')
    user_type = request.cookies.get('user_type')
    course_name = request.cookies.get('course_name')
    _date = request.cookies.get('date')
    app.config['UPLOADED_FILES_DEST'] = path.join(dir, str(course_id))
    configure_uploads(app, files)
    if request.method == 'POST' and 'file' in request.files:
        try:
            info = request.form.to_dict()
            file = request.files['file']
            filename = files.save(request.files['file'], name=file.filename)
            _path = app.config['UPLOADED_FILES_DEST']
            _type = filename.rsplit('.', 1)[1].lower()
            chapter = request.form['sel']
            name = filename.rsplit('.', 1)[0]
            size = path.getsize(files.path(filename))
            length = 0
            res = 1
            if "restriction" in info:
                res=0
            if _type in VIDEOS:
                preview = 1
                clip=VideoFileClip(_path+"/"+filename)
                length=clip.duration
            elif _type in PDF:
                preview = 1
            else:
                preview = 0
            if request.form['description']:
                description = request.form['description']
                sql = "INSERT INTO source(user_id, user_type,path,type,chapter,name,course_id,size,description," \
                      "preview,length,browse_restrict)VALUES(%s,'%s','%s','%s',%s,'%s',%s,%s,'%s',%s,%s, %s)" % (
                        user_id, user_type, _path, _type, chapter, name, course_id, size, description, preview, length,
                        res)
            else:
                sql = "INSERT INTO source(user_id, user_type,path,type,chapter,name,course_id,size, preview," \
                      "length, browse_restrict) " \
                      "VALUES(%s,'%s','%s','%s',%s,'%s',%s,%s, %s,%s, %s)" % (
                        user_id, user_type, _path, _type, chapter, name, course_id, size, preview, length, res)
            cursor.execute(sql)
            db.commit()
            flash("上传成功", category="success")
        except UploadNotAllowed as e:
            flash("上传失败，不允许上传的文件类型", category='error')
    sql = "select max_chapters from numberofchapters where course_id=%s" % course_id
    cursor.execute(sql)
    numbers = cursor.fetchone()
    if not numbers:
        sql = "insert into numberofchapters values(%s, %s)" %(course_id, 1)
        n=1;
    else:
        n=numbers[0]
    sql = "select * from detailchapters where course_id=%s order by chapter ASC" % course_id
    cursor.execute(sql)
    descriptions = cursor.fetchall()
    sources = []
    for i in range(n):
        sql = "select * from source where course_id=%s and chapter=%s" % (course_id, i+1)
        cursor.execute(sql)
        sources.append(cursor.fetchall())
    response = make_response(render_template('source_control.html', number=n, chapters=descriptions, files=sources))
    response.set_cookie('course_id', course_id)
    response.set_cookie('user_id', user_id)
    response.set_cookie('user_type', user_type)
    response.set_cookie('course_name', course_name)
    response.set_cookie('date', _date)
    return response


@app.route('/sources/chapters', methods=['POST'])
def chapters_modify():
    course_id = request.cookies.get('course_id')
    user_id = request.cookies.get('user_id')
    user_type = request.cookies.get('user_type')
    if request.method == 'POST':
        sql = "select max_chapters from numberofchapters where course_id=%s" % course_id
        cursor.execute(sql)
        numbers = cursor.fetchone()
        number = numbers[0]
        for i in range(number):
            name = "chapter" + str(i+1)
            if request.form[name]:
                sql = "select * from detailchapters where course_id=%s and chapter=%s" % (
                    course_id, i+1
                )
                cursor.execute(sql)
                if cursor.fetchall():
                    sql = "update detailchapters set description='%s' where course_id=%s and chapter=%s" % (
                        request.form[name], course_id, i+1
                    )
                else:
                    sql = "insert into detailchapters values(%s,%s,'%s')" % (
                        course_id,  i + 1, request.form[name]
                    )
                cursor.execute(sql)
        if request.form['numberofchapters']:
            sql = "update numberofchapters set max_chapters=%s where course_id=%s" % (request.form['numberofchapters'],
                                                                                      course_id)
            cursor.execute(sql)
    db.commit()
    flash('修改成功', category="success")
    return redirect(url_for('upload_file'))


@app.route('/sources/modify', methods=['POST'])
def modify():
    course_id = request.cookies.get('course_id')
    info = request.form.to_dict()
    filename = request.form['source']
    _type = filename.rsplit('.', 1)[1].lower()
    name = filename.rsplit('.', 1)[0]
    res=1
    if "restriction" in info:
        res = 0
    if request.form['chapters']:
        chapter=request.form['chapters']
        sql="update source set browse_restrict=%s, chapter=%s where type='%s' and name='%s' and" \
            "course_id=%s" % (res, chapter, _type, name, course_id)
        cursor.execute(sql)
    if request.form['description']:
        desp=request.form['description']
        sql = "update source set browse_restrict=%s, description='%s' where type='%s' and" \
              " name='%s'and course_id=%s" % (res, desp, _type, name, course_id)
        cursor.execute(sql)
    db.commit()
    flash("修改成功", category="success")
    return redirect(url_for('upload_file'))


@app.route('/sources/delete', methods=['POST'])
def delete():
    filename=request.form['source']
    url= app.config['UPLOADED_FILES_DEST'] + "/" + filename
    _type = filename.rsplit('.', 1)[1].lower()
    name = filename.rsplit('.', 1)[0]
    remove(url)
    sql="delete from source where type='%s' and name='%s'" % (_type, name)
    cursor.execute(sql)
    db.commit()
    flash('删除成功', category="success")
    return redirect(url_for('upload_file'))


@app.route('/getfile/<filename>')
def getfile(filename):
    _type = filename.rsplit('.', 1)[1].lower()
    name = filename.rsplit('.', 1)[0]
    sql="select browse_restrict from source where type='%s' and name='%s'" % (_type, name)
    cursor.execute(sql)
    bs=cursor.fetchone()[0]
    if bs == 1 and request.cookies.get('user_type') == 'V':
        flash("该资源不允许游客浏览和下载，请先登录！", category="error")
        return render_template('error.html')
    return send_from_directory(app.config['UPLOADED_FILES_DEST'], filename)


@app.route('/pdf/<filename>')
def show(filename):
    if filename is None:
        return render_template('404.html')
    course_id = request.cookies.get('course_id')
    _type = filename.rsplit('.', 1)[1].lower()
    name = filename.rsplit('.', 1)[0]
    sql="select browse_restrict from source where course_id=%s and type='%s' and name='%s'" % (course_id, _type, name)
    cursor.execute(sql)
    bs = cursor.fetchone()[0]
    if bs == 1 and request.cookies.get('user_type') == 'V':
        flash("该资源不允许游客浏览和下载，请先登录！", category="error")
        return render_template('error.html')
    url = url_for('static', filename='sources/'+str(course_id)+'/'+filename)
    return render_template('show.html', url=url, name=filename)


@app.route('/video/<filename>')
def play(filename):
    if filename is None:
        return render_template('404.html')
    course_id = request.cookies.get('course_id')
    _type = filename.rsplit('.', 1)[1].lower()
    name = filename.rsplit('.', 1)[0]
    sql="select browse_restrict from source where course_id=%s and type='%s' and name='%s'" % (course_id, _type, name)
    cursor.execute(sql)
    bs = cursor.fetchone()[0]
    if bs == 1 and request.cookies.get('user_type') == 'V':
        flash("该资源不允许游客浏览和下载，请先登录！", category="error")
        return render_template('error.html')
    url = url_for('static', filename='sources/'+str(course_id)+'/'+filename)
    return render_template('play.html', url=url, name=filename, tp=_type)


@app.route('/question_set_list/<c_id><s_id>')
def question_set_list(c_id, s_id):
    results = get_queset_list(c_id)
    return render_template('stu_question_set_list.html', user_id=s_id, course_id=c_id, queset=results)


@app.route('/question_set', methods=['GET', 'POST'])
def question_set():
    if request.method == 'GET':
        queset_id = request.args.get('queset_id')
        user_id = request.args.get('user_id')
        queset = get_queset(queset_id)
        question_list = get_question_list(queset_id)
        answerset = get_answerset(user_id, queset_id)
        if answerset:
            answerset_id = answerset[2]
            answer_list = get_answer_list(answerset_id)
            # print(answer_list)
            return render_template('stu_question_set.html', queset=queset, answerset=answerset, question_list=question_list, answer_list=answer_list, user_id=user_id)
        else:
            return render_template('stu_question_set.html', queset=queset, answerset=answerset, question_list=question_list, answer_list=None, user_id=user_id)
    elif request.method == 'POST':
        form = request.form.to_dict()
        upload_question_id = get_upload_question_id(form['queset_id'])
        for each_id in upload_question_id:
            fid = str(each_id[0])
            if request.files[fid].filename != '':
                form[fid] = request.files[fid].filename
                homework_save(form['user_id'] + "_" + form['queset_id'], request.files[fid])
        add_answer(form)
        return render_template('submit_success.html')


homeworks = UploadSet('HOMEWORKS', ALL)


@app.route('/download_homework/<user_id>_<queset_id>_<question_id>_<answerset_id>')
def download_homework(user_id, queset_id, question_id, answerset_id):
    db = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = db.cursor()
    sql = "SELECT content FROM answer WHERE answerset_id = %s and question_id = %s" % (answerset_id, question_id)
    cursor.execute(sql)
    filename = cursor.fetchone()[0]
    db.close()
    app.config['UPLOADED_HOMEWORKS_DEST'] = path.join(path.dirname(path.abspath(__file__)), "homeworks/" + user_id + "_" + queset_id)
    configure_uploads(app, homeworks)
    return send_from_directory(app.config['UPLOADED_HOMEWORKS_DEST'], filename)


@app.route('/log')
def log():
    return send_from_directory("/srv/TS/log/", "app.log")


def homework_save(directory=None, file=None):
    app.config['UPLOADED_HOMEWORKS_DEST'] = path.join(path.dirname(path.abspath(__file__)), "homeworks/" + directory)
    configure_uploads(app, homeworks)
    if path.exists(app.config['UPLOADED_HOMEWORKS_DEST'] + "\\" + file.filename):
        remove(app.config['UPLOADED_HOMEWORKS_DEST'] + "\\" + file.filename)
    homeworks.save(file, name=file.filename)


def get_queset_list(course_id):
    db = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = db.cursor()
    sql = "SELECT * FROM queset WHERE course_id = %s" % course_id
    cursor.execute(sql)
    queset = cursor.fetchall()
    db.close()
    return queset


def get_queset(queset_id):
    db = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = db.cursor()
    sql = "SELECT * FROM queset WHERE id = %s" % queset_id
    cursor.execute(sql)
    queset = cursor.fetchone()
    db.close()
    return queset


def get_upload_question_id(queset_id):
    db = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = db.cursor()
    sql = "SELECT id FROM question WHERE queset_id = %s and type = 3" % queset_id
    cursor.execute(sql)
    upload_question_id = cursor.fetchall()
    db.close()
    return upload_question_id


def get_answerset(user_id, queset_id):
    db = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = db.cursor()
    sql = "SELECT * FROM answerset WHERE student_id = %s and queset_id = %s" % (user_id, queset_id)
    cursor.execute(sql)
    answerset = cursor.fetchone()
    db.close()
    return answerset


def get_answer_list(answerset_id):
    db = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = db.cursor()
    sql = "SELECT * FROM answer WHERE answerset_id = %s" % answerset_id
    cursor.execute(sql)
    answer_list = cursor.fetchall()
    db.close()
    return answer_list


def get_question_list_by_type(queset_id, question_type):
    db = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = db.cursor()
    sql = "SELECT * FROM question WHERE queset_id = %s AND type = %s" % (queset_id, question_type)
    cursor.execute(sql)
    question_list = cursor.fetchall()
    db.close()
    return question_list


def get_question_list(queset_id):
    question_choice_list = get_question_list_by_type(queset_id, 0)
    question_input_list = get_question_list_by_type(queset_id, 1)
    question_judge_list = get_question_list_by_type(queset_id, 2)
    question_upload_list = get_question_list_by_type(queset_id, 3)
    question_list = {'choice': question_choice_list, 'judge': question_judge_list, 'input': question_input_list,
                     'upload': question_upload_list}
    return question_list


def add_answer(answers):
    user_id = answers.pop('user_id')
    queset_id = answers.pop('queset_id')
    db = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = db.cursor()

    sql = "INSERT INTO answerset(student_id, queset_id, submit_time) VALUES (%s, %s, now()) ON DUPLICATE KEY UPDATE submit_time = now()" % (user_id, queset_id)
    try:
        cursor.execute(sql)
        db.commit()
    except:
        db.rollback()

    cursor = db.cursor()
    sql = "SELECT id FROM answerset WHERE student_id = %s AND queset_id = %s" % (user_id, queset_id)
    cursor.execute(sql)
    answerset_id = cursor.fetchone()[0]

    cursor = db.cursor()

    for key in answers.keys():
        content = answers[key]
        sql = "INSERT INTO answer(answerset_id, question_id, content, state) VALUES (%s, %s, %s, %s) " \
              "ON DUPLICATE KEY UPDATE content = %s" % (answerset_id, key, "'" + content + "'", 1, "'" + content + "'")
        cursor.execute(sql)
        db.commit()
    db.close()

#admin部分——后台管理
#admin部分——后台管理

# 要求登录才能访问
def admin_login_require(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if session.get('login_admin', None) is None:
            # 如果session中未找到该键，则用户需要登录
            return redirect(url_for('user.login'))
        return func(*args, **kwargs)
    return decorated_function



@app.route("/admin")
@admin_login_require
@permission_required(Permission.ADMINISTRATOR)
def index():
    return render_template('admin/index.html')


'''''
@admin.route("/", methods=['GET', 'POST'])
def login():
    if request.method=='POST':
        name=request.form.get('name')
        pwd=request.form.get('pwd')
        # print(data)
        login_admin = User.query.filter_by(name=name).first()
        if login_admin.passwd!=pwd or login_admin.type!='A':
            # 判断密码错误，然后将错误信息返回，使用flash用于消息闪现
            flash('密码错误！')
            return redirect(url_for('admin.login'))
        # 如果密码正确，session中添加账号记录，然后跳转到request中的next，或者是跳转到后台的首页
        else:
            login_user(login_admin)
            session['login_admin'] = name
            return redirect( url_for('admin.index'))
    return render_template('admin/login.html')
'''




@app.route("/admin/user/list/<int:page>/",methods=["GET", "POST"])
@admin_login_require
@permission_required(Permission.ADMINISTRATOR)
def user_list(page=None):
    if request.method == 'POST':
        list = request.files.get('userlist')
        list = io.StringIO(list.stream.read().decode("UTF-8"), newline=None)
        if list:
            print('sss')
            portfolios = csv.DictReader(list)
            # load csv file in dictionary
            for row in portfolios:
                print(row)
                name = row['name']
                pwd = row['password']
                type = row['type']
                ID = int(row['id'])
                gender = row['gender']
                age = int(row['age'])
                affiliation = row['affiliation']
                re=User.query.filter_by(name=name)
                if re:
                    continue
                user = User(name=name, passwd=pwd, type=type, ID=ID, gender=gender, age=age, affiliation=affiliation,
                            legality=True)
                db1.session.add(user)
            db1.session.commit()
        return redirect(url_for('user_list', page=1))
    if page is None:
        page = 1
    page_users = User.query.filter_by(legality=True).paginate(page=page, per_page=10)
    return render_template('admin/user_list.html', page_users=page_users)




#lazy delete
@app.route("/admin/user/delete/<string:delete_id>/",methods=["GET", "POST"])
@admin_login_require
@permission_required(Permission.ADMINISTRATOR)
def user_delete(delete_id=None):
    users = User.query.filter_by(name=delete_id)
    for u in users:
        if u.type!='A':
            u.legality=False
            db1.session.add(u)
            # 删除后闪现消息
            flash('删除用户成功！', category='ok')
        else:#user是管理员不能删除
            flash('您无此删除此用户权限',category='err')
    db1.session.commit()
    return redirect(url_for('user_list', page=1))

@app.route("/admin/user/thaw/<string:thaw_id>/",methods=["GET", "POST"])
@admin_login_require
@permission_required(Permission.ADMINISTRATOR)
def user_thaw(thaw_id=None):
    users = User.query.filter_by(name=thaw_id)
    for u in users:
        if u.type!='A':
            u.legality=False
            flash('冻结账号成功！', category='ok')
            db1.session.add(u)
        else:
            flash('您无此操作权限!',category='err')
    db1.session.commit()
    return redirect(url_for('user_list', page=1))


@app.route("/admin/user/unthaw/<string:unthaw_id>/",methods=["GET", "POST"])
@admin_login_require
@permission_required(Permission.ADMINISTRATOR)
def user_unthaw(unthaw_id=None):
    users = User.query.filter_by(name=unthaw_id)
    for u in users:
        if u.type != 'A':
            u.legality=True
            flash('账号解冻成功！', category='ok')
            db1.session.add(u)
        else:
            flash('您无此操作权限!',category='err')
    db1.session.commit()
    return redirect(url_for('user_list', page=1))


#全部采用lazy delete方式
@app.route("/admin/message/<int:delete_id>/",methods=["GET", "POST"])
@admin_login_require
@permission_required(Permission.ADMINISTRATOR)
def message_delete(delete_id=None):
    messages = Message.query.filter_by(random_id=delete_id)
    for m in messages:
        m.isdeleted=1
        flash('游客留言删除成功！')
        db1.session.add(m)
    db1.session.commit()
    return redirect(url_for('message_list', page=1))

@app.route("/admin/comments/<int:delete_id><int:uid>/",methods=["GET", "POST"])
@admin_login_require
@permission_required(Permission.ADMINISTRATOR)
def discussion_delete(delete_id=None,uid=None):
    messages = Discussion.query.filter_by(num=delete_id,uid=uid)
    print(delete_id,uid,messages)
    for m in messages:
        m.isdeleted=1
        flash('用户留言删除成功！')
        db1.session.add(m)
    db1.session.commit()
    return redirect(url_for('discussion_list', page=1))

@app.route("/admin/cmessage/<int:delete_id>/",methods=["GET", "POST"])
@admin_login_require
@permission_required(Permission.ADMINISTRATOR)
def cmessage_delete(delete_id=None):
    cmessages = Cmessage.query.filter_by(random_id=delete_id)
    for m in cmessages:
        m.isdeleted=1
        db1.session.add(m)
        flash('用户留言删除成功！')
    db1.session.commit()
    return redirect(url_for('cmessage_list', page=1))

@app.route("/admin/notice/<int:delete_id>/",methods=["GET", "POST"])
@admin_login_require
@permission_required(Permission.ADMINISTRATOR)
def notice_delete(delete_id=None):
    notices = Notice.query.filter_by(num=delete_id)
    for m in notices:
        m.isdeleted=1
        db1.session.add(m)
        flash('用户留言删除成功！')
    db1.session.commit()
    return redirect(url_for('notice_list', page=1))

@app.route("/admin/message/list/<int:page>/",methods=['GET', 'POST'])
@admin_login_require
def message_list(page=None):
    if not page:
        page = 1
    page_messages = Message.query.filter_by(isdeleted=0).paginate(page=page, per_page=10)
    return render_template('admin/message_list.html', page_messages=page_messages)


@app.route("/admin/discussion/list/<int:page>/",methods=['GET', 'POST'])
@admin_login_require
def discussion_list(page=None):
    if not page:
        page = 1
    page_discussions = Discussion.query.filter_by(isdeleted=0).paginate(page=page, per_page=10)
    return render_template('admin/discussion_list.html', page_discussions=page_discussions)


@app.route("/admin/cmessage/list/<int:page>/",methods=['GET', 'POST'])
@admin_login_require
def cmessage_list(page=None):
    if not page:
        page = 1
    page_cmessages = Cmessage.query.filter_by(isdeleted=0).paginate(page=page, per_page=10)
    return render_template('admin/cmessage_list.html', page_cmessages=page_cmessages)


@app.route("/admin/notice/list/<int:page>/",methods=['GET', 'POST'])
@admin_login_require
def notice_list(page=None):
    if request.method=='POST':
        content=request.form.get('content')
        notice=Notice(mid=current_user.ID,num=None,content=content,time=datetime.date.today(),isdeleted=0)
        db1.session.add(notice)
        db1.session.commit()
        return redirect(url_for('notice_list',page=1))
    if not page:
        page = 1
    page_notices = Notice.query.filter_by(isdeleted=0).paginate(page=page, per_page=10)
    return render_template('admin/notice_list.html', page_notices=page_notices)






@app.route("/admin/role/list/<int:page>/",methods=['GET', 'POST'])
@admin_login_require
def role_list(page=None):
    if request.method=='POST':
        value=0
        auth=request.values.getlist('authority')
        rolename=request.form.get('usertype')
        if auth:
            if (rolename=='A' and current_user.name=='admin001') or rolename!='A':
                for i in range(0,len(auth)):
                    print(auth[i])
                    value|=int(auth[i])
                role=Role.query.filter_by(type=rolename).first()
                role.permissions=value
                db1.session.add(role)
                db1.session.commit()
                flash('权限更改成功！',category='ok')
            else:
                flash('权限更改失败！',category='err')
    if not page:
        page = 1
    page_roles = Role.query.paginate(page=page, per_page=10)
    return render_template('admin/role_list.html', page_roles=page_roles)

@app.route('/notice_show')
def notice_show():
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    sql1 = "select * from notice where isdeleted = 0"

    # 执行sql语句
    my_connect.ping(reconnect=True)
    cursor.execute(sql1)
    my_connect.commit()
    # 执行sql语句
    result = cursor.fetchall()
    print(result)

    cursor.close()
    my_connect.close()

    return render_template('m_notice.html', record=result)

@app.route('/notice_post')
def notice_post():
    content = request.args.get('content')
    print(content)
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()

    current = datetime.date.today()
    cursor.execute("select num from notice")

    number = 0
    while True:
        set = cursor.fetchone()
        number = number + 1
        if not set:
            break

    print(number)
    sql2 = "insert into notice (mid,content,time,num,isdeleted) values ('%s','%s','%s','%s','%s')" % (100, content, current, number,0)
    print(sql2)
    cursor.execute(sql2)
    my_connect.commit()
    cursor.close()
    my_connect.close()

    return render_template('npost_success.html')

@app.route('/message_view')
def message_view():
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    sql1 = "select * from message where isdeleted = 0"

    # 执行sql语句
    my_connect.ping(reconnect=True)
    cursor.execute(sql1)
    my_connect.commit()
    # 执行sql语句
    result = cursor.fetchall()
    print(result)

    cursor.close()
    my_connect.close()

    return render_template('visitor_message.html', record=result)

@app.route('/post_message')
def post_message():
    content = request.args.get('content')
    print(content)
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()

    current = datetime.date.today()
    cursor.execute("select random_id from message")

    number = 0
    while True:
        set = cursor.fetchone()
        number = number + 1
        if not set:
            break

    print(number)
    sql2 = "insert into message (random_id,content,time,isdeleted) values ('%s','%s','%s','%s')" % (number, content, current,0)
    print(sql2)
    cursor.execute(sql2)
    my_connect.commit()
    cursor.close()
    my_connect.close()

    return render_template('visitor_message.html')

@app.route('/discussion/<c_id><u_id>')
def discussion(c_id, u_id):
    print(c_id)
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    sql1 = "select * from discussion where cid='%s' and isdeleted = 0" % (c_id)

    # 执行sql语句
    my_connect.ping(reconnect=True)
    cursor.execute(sql1)
    my_connect.commit()
    # 执行sql语句
    result = cursor.fetchall()
    print(result)

    my_connect.commit()
    sql2 = "select name from user where ID='%s'" % (u_id)
    cursor.execute(sql2)
    u_name = cursor.fetchone()

    cursor.close()
    my_connect.close()

    return render_template('discussion.html', record=result, u_id=u_id,c_id=c_id,u_name = u_name)
@app.route('/post_dis')
def post_dis():
    c_id = request.args.get('c_id')
    u_id = request.args.get('u_id')
    content = request.args.get('content')
    print(c_id,u_id)
    print(content)
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    sql1 = "select name from user where ID='%s'" % (u_id)
    cursor.execute(sql1)
    name = cursor.fetchone()
    current = datetime.date.today()
    cursor.execute("select num from discussion")

    number = 0
    while True:
        set = cursor.fetchone()
        number = number + 1
        if not set:
            break

    print(number)
    sql2 = "insert into discussion (num,chapter,cid,uid,uname,content,time,replyto,isdeleted) values ('%s','%s','%s','%s','%s','%s','%s','%s','%s')"%(number,5,c_id,u_id,name[0],content,current,-1,0)
    print(sql2)
    cursor.execute(sql2)
    my_connect.commit()
    cursor.close()
    my_connect.close()

    return render_template('discussion.html')

@app.route('/evaluation/<c_id>')
def evaluation(c_id):
    print(c_id)
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()
    sql1 = "select * from cmessage where cid='%s' and isdeleted = 0" % (c_id)

    # 执行sql语句
    my_connect.ping(reconnect=True)
    cursor.execute(sql1)
    my_connect.commit()
    # 执行sql语句
    result = cursor.fetchall()
    print(result)

    cursor.close()
    my_connect.close()

    return render_template('cmessage.html', record=result,c_id=c_id)


@app.route('/post_cmsg')
def post_cmesg():
    c_id = request.args.get('c_id')
    content = request.args.get('content')
    print(c_id)
    print(content)
    my_connect = pymysql.connect(my_host, my_user, my_password, my_db)
    cursor = my_connect.cursor()

    current = datetime.date.today()
    cursor.execute("select random_id from cmessage")

    number = 0
    while True:
        set = cursor.fetchone()
        number = number + 1
        if not set:
            break

    print(number)
    sql2 = "insert into cmessage (random_id,cid,content,time,isdeleted) values ('%s','%s','%s','%s','%s')"%(number,c_id,content,current,0)
    print(sql2)
    cursor.execute(sql2)
    my_connect.commit()
    cursor.close()
    my_connect.close()

    return render_template('cmessage.html')

if __name__ == '__main__':
    app.run()

