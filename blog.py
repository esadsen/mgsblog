from logging import log
from flask import Flask,render_template,flash,redirect,url_for,logging,request,session
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps
class RegisterForm(Form):
    name=StringField("İsim Soyisim",validators=[validators.Length(min=4,max=25)])
    username=StringField("Kullanıcı adı",validators=[validators.Length(min=4,max=25)])
    email=StringField("Email",validators=[validators.Email(message="Lütfen geçerli bir email girin")])
    password=PasswordField("Parola:",validators=[
        validators.DataRequired(message="Lütfen bir parola belirleyin"),
        validators.EqualTo(fieldname="confirm",message="Parolanız uyuşmuyor")

    ])
    confirm=PasswordField("Parola Doğrula")
class LoginForm(Form):
    username=StringField("Kullanıcı Adı")
    password=PasswordField("Parola")
class ArticleForm(Form):
    title=StringField("Makale Başlığı",validators=[validators.length(min=3,max=50)])
    content=TextAreaField("Makale İçeriği",validators=[validators.length(min=10)])

app=Flask(__name__)

app.secret_key="mgsblog"
app.config["MYSQL_HOST"]="localhost"
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"]="mgsblog"
app.config["MYSQL_CURSORCLASS"]="DictCursor"

mysql=MySQL(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek lütfen giriş yapınız...","danger")
            return redirect(url_for("login"))
    return decorated_function

@app.route("/")
def index():
    return render_template("index.html")
@app.route("/about")
def about():
    return render_template("about.html")
@app.route("/articles/<string:id>")
def detail(id):
    return "Article Id: " + id
@app.route("/register",methods=["GET","POST"])
def register():
    form=RegisterForm(request.form)
    if request.method=="POST" and form.validate():
        name=form.name.data
        username=form.username.data
        email=form.email.data
        password=sha256_crypt.encrypt(form.password.data)

        cursor=mysql.connection.cursor()
        sorgu="INSERT INTO users(name,username,email,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(sorgu,(name,username,email,password))
        mysql.connection.commit()
        cursor.close()

        flash("Başarıyla kayıt oldunuz","success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html",form=form)
@app.route("/login",methods=["GET","POST"])
def login():
    form=LoginForm(request.form)
    if request.method=="POST":
        username=form.username.data
        password_entered=form.password.data
        cursor=mysql.connection.cursor()
        sorgu="SELECT * FROM users where username=%s"
        result=cursor.execute(sorgu,(username,))
        if result > 0:
            data=cursor.fetchone()
            real_password=data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Başarıyla giriş yaptınız...","success")

                session["logged_in"]=True
                session["username"]=username

                return redirect(url_for("index"))
            else:
                flash("Parola hatalı lütfen tekrar deneyin","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor...","danger")
            return redirect(url_for("login"))

    
    return render_template("login.html",form=form)
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
@app.route("/dashboard")
@login_required
def dashboard():
    cursor=mysql.connection.cursor()
    sorgu="SELECT * FROM articles where author = %s"
    result=cursor.execute(sorgu,(session["username"],))
    if result >0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")
@app.route("/addarticle",methods=["GET","POST"])
def addarticle():
    form=ArticleForm(request.form)
    if request.method=="POST" and form.validate():
        title=form.title.data
        content=form.content.data
        
        cursor=mysql.connection.cursor()
        sorgu="INSERT INTO articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()

        flash("Makale başarıyla eklendi","success")
        return redirect(url_for("dashboard"))
    return render_template("addarticle.html",form=form)
@app.route("/articles")
def articles():
    cursor=mysql.connection.cursor()
    sorgu="SELECT * FROM articles"
    result=cursor.execute(sorgu)
    if result > 0:
        articles=cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")
@app.route("/article/<string:id>")
def article(id):
    cursor=mysql.connection.cursor()
    sorgu="SELECT * FROM articles WHERE id = %s"
    result=cursor.execute(sorgu,(id,))
    if result >0:
        article=cursor.fetchone()
        return render_template("article.html",article=article)
    else:
        return render_template("article.html")
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor=mysql.connection.cursor()
    sorgu="SELECT * FROM articles WHERE author = %s AND id = %s"
    result=cursor.execute(sorgu,(session["username"],id))
    if result >0:
        sorgu2="DELETE FROM articles WHERE id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok ya da bu işlem için yetkiniz yok...","danger")
        return redirect(url_for("index"))
@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def update(id):
    if request.method=="GET":
        cursor=mysql.connection.cursor()
        sorgu="SELECT * FROM articles WHERE id = %s and author=%s"
        result=cursor.execute(sorgu,(id,session["username"]))
        if result==0:
            flash("Böyle bir makale yok ya da bu işleme yetkiniz yok...","danger")
            return redirect(url_for("index"))
        else:
            article=cursor.fetchone()
            form = ArticleForm()
            form.title.data=article["title"]
            form.content.data=article["content"]
            return render_template("update.html",form=form)
    else:
        form=ArticleForm(request.form)
        newTitle=form.title.data
        newContent=form.content.data
        sorgu2="UPDATE articles SET title=%s,content=%s WHERE id=%s"
        cursor=mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()
        flash("Makale başarıyla güncellendi","success")
        return redirect(url_for("dashboard"))       

if __name__=="__main__":
    app.run(debug=True)
