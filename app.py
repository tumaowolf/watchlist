"""program index"""
import os
import sys
import click
from flask import Flask,render_template,request,url_for,redirect,flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import LoginManager,UserMixin,login_user


WIN = sys.platform.startswith('win')
if WIN: #如果是windows系统，使用三个斜线
    prefix = 'sqlite:///'
else:   #否则使用四个斜线
    prefix = 'sqlite:////'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(app.root_path,'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False    #关闭对模型修改的监控
app.config['SECRET_KEY'] = 'dev'
#在扩展类实例化前加载配置
db = SQLAlchemy(app)
login_manager = LoginManager(app)

@app.cli.command()  #注册为命令
@click.option('--drop',is_flag=True,help='Create after drop.')  #设置选项
def initdb(drop):
    """Initialize the database"""
    if drop:
        db.drop_all()
    db.create_all()
    click.echo('Initialized database.')

@app.cli.command()
def forge():
    """Generate fake data."""
    db.create_all()

    name = 'tumao wolf'
    movies = [
        {'title': 'My Neighbor Totoro', 'year': '1999'},
        {'title': 'Dead Poets Society', 'year': '1989'},
        {'title': 'A Perfect World', 'year': '1993'},
        {'title': 'Leon', 'year': '1994'},
        {'title': 'Mahjong', 'year': '1996'},
        {'title': 'Swallowtail Butterfly', 'year': '1996'},
        {'title': 'King of Comedy', 'year': '1999'},
        {'title': 'Devils on the Doorstep', 'year': '1999'},
        {'title': 'WALL-E', 'year': '2008'},
        {'title': 'The Pork of Music', 'year': '2012'},
    ]

    user = User(name=name)
    db.session.add(user)
    for m in movies:
        movie = Movie(title=m['title'],year=m['year'])
        db.session.add(movie)

    db.session.commit()
    click.echo('Done.')


#创建数据库模型
class User(db.Model,UserMixin):    #表名将会是user
    id = db.Column(db.Integer,primary_key=True)     #主键
    name = db.Column(db.String(20))                 #名字
    username = db.Column(db.String(20))             #用户名
    password_hash = db.Column(db.String(128))       #密码散列值

    def set_password(self,password):    #用来设置密码的方式，接收密码作为参数
        self.password_hash = generate_password_hash(password)   #将生成的密码保持到对应字段

    def validate_password(self,password):
        return check_password_hash(self.password_hash,password)

class Movie(db.Model):  #表名将会是movie
    id = db.Column(db.Integer,primary_key=True)     #主键
    title = db.Column(db.String(60))    #电影标题
    year = db.Column(db.String(4))      #电影年份

@app.context_processor
def inject_user():  #函数名可以随意修改
    user = User.query.first()
    return dict(user=user)

@app.route('/',methods=['GET','POST'])
def index():
    if request.method == 'POST':
        #获取表单数据
        title = request.form.get('title')
        year = request.form.get('year')
        #验证数据
        if not title or not year or len(year) > 4 or len(title) > 60:
            flash('Invalid title or year!')     #显示错误提示
            return redirect(url_for('index'))   #重定向回主页
        #保存表单数据到数据库
        movie = Movie(title=title,year=year)    #创建记录
        db.session.add(movie)                   #添加到数据库会话
        db.session.commit()                     #提交数据库会话
        flash('Item created.')                  #显示成功创建的提示
        return redirect(url_for('index'))       #重定向回主页

    user = User.query.first()
    movies = Movie.query.all()
    return render_template('index.html',user=user,movies=movies)


@app.errorhandler(404)  #传入要处理的错误代码
def page_not_found(e):  #接收异常对象作为参数
    return render_template('404.html'),404    #返回模板和状态码


@app.route('/movie/edit/<int:movie_id>',methods=['GET','POST'])
def edit(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    if request.method == 'POST':
        title = request.form['title']
        year = request.form['year']

        if not title or not year or len(year) > 4 or len(title) > 60:
            flash('Invalid input.')
            return redirect(url_for('edit',movie_id=movie_id))

        movie.title = title     #更新标题
        movie.year = year       #更新年份
        db.session.commit()     #提交数据库会话
        flash('Item updated.')
        return redirect(url_for('index'))

    return render_template('edit.html',movie=movie)

@app.route('/movie/delete/<int:movie_id>',methods=['POST'])     #限定只接受POST请求
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    db.session.delete(movie)    #删除对应的记录
    db.session.commit()     #提交数据库会话
    flash('Item deleted.')
    return redirect(url_for('index'))   #重定向回主页

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Invalid input.')
            return redirect(url_for('login'))

        user = User.query.first()
        #验证用户名和密码是否一致
        if username == user.username and user.validate_password(password):
            login_user(user)
            flash('Login success.')
            return redirect(url_for('index'))

        flash('Invalid username or password.')
        return redirect(url_for('login'))

    return render_template('login.html')

"""生成管理员账户"""
@app.cli.command()
@click.option('--username',prompt=True,help='The username used to login.')
@click.option('--password',prompt=True,hide_input=True,confirmation_prompt=True,
              help='The password used to login.')
def admin(username,password):
    """Create user."""
    db.create_all()

    user = User.query.first()
    if user is not None:
        click.echo('Updating user...')
        user.username = username
        user.set_password(password)
    else:
        click.echo('Creating user...')
        user = User(username=username,name='Admin')
        user.set_password(password)
        db.session.add(user)

    db.session.commit()     #提交数据库会话
    click.echo('Done.')

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    return user

if __name__ == '__main__':
    app.run()