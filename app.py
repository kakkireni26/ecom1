from flask import Flask,request,render_template,redirect,url_for,flash,session
from otp import genotp
from cmail import sendmail
from token_1 import encode,decode
import os
#import razorpay
import re
import mysql.connector
from mysql.connector import (connection)
# mydb= connection.MySQLConnection(user='root', password='admin',host='localhost',database='ecommee')
app=Flask(__name__)
app.secret_key='code@123'
app.config['SESSION_TYPE']='filesystem'
#client = razorpay.Client(auth=("rzp_test_YHO379ztVK64ZN","C4aXFH2ZhukVxnudToAasqU2"))

user=os.environ.get('RDS_USERNAME')
db=os.environ.get('RDS_DB_NAME')
password=os.environ.get('RDS_PASSWORD')
host=os.environ.get('RDS_HOSTNAME')
port=os.environ.get('RDS_PORT')
with mysql.connector.connect(host=host,password=password,db=db,user=user) as conn:
    cursor=conn.cursor()
    cursor.execute("CREATE TABLE if not exists admincreate(email varchar(50) NOT NULL,username varchar(100) NOT NULL,password varbinary(10) NOT NULL,address text NOT NULL,accept enum('on','off') DEFAULT NULL,dp_image varchar(50) DEFAULT NULL,PRIMARY KEY(email)")
    cursor.execute("CREATE TABLE if not exists items (item_id binary(16) NOT NULL,item_name varchar(255) NOT NULL,quantity int unsigned DEFAULT NULL,price decimal(14,4) NOT NULL,category enum('Home_appliances','Electronics','Fashion','Grocery') DEFAULT NULL,image_name varchar(255) NOT NULL,added_by varchar(50) DEFAULT NULL,description longtext,PRIMARY KEY (item_id),KEY added_by (added_by),CONSTRAINT items_ibfk_1 FOREIGN KEY (added_by) REFERENCES admincreate (email) ON DELETE CASCADE ON UPDATE CASCADE")
    cursor.execute("CREATE TBALE if not exists usercreate (username varchar(50) NOT NULL,user_email varchar(100) NOT NULL,address text NOT NULL,password varbinary(20) NOT NULL,gender enum('Male','Female') DEFAULT NULL,PRIMARY KEY (user_email),UNIQUE KEY username (username)")
    cursor.execute("CREATE TABLE if not exists orders (orderid bigint NOT NULL AUTO_INCREMENT,itemid binary(16) DEFAULT NULL,item_name longtext,qty int DEFAULT NULL,total_price bigint DEFAULT NULL,user varchar(100) DEFAULT NULL,PRIMARY KEY (orderid),KEY user (user),KEY itemid (itemid),CONSTRAINT orders_ibfk_1 FOREIGN KEY (user) REFERENCES usercreate (user_email),CONSTRAINT orders_ibfk_2 FOREIGN KEY (itemid) REFERENCES items (item_id)")
    cursor.execute("CREATE TABLE if not exists reviews (username varchar(50) NOT NULL,itemid binary(16) NOT NULL,title tinytext,review text,rating int DEFAULT NULL,date datetime DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY (itemid,username),KEY username (username),CONSTRAINT reviews_ibfk_1 FOREIGN KEY (itemid) REFERENCES items (item_id) ON DELETE CASCADE ON UPDATE CASCADE,CONSTRAINT reviews_ibfk_2 FOREIGN KEY (username) REFERENCES usercreate (user_email) ON DELETE CASCADE ON UPDATE CASCADE)")
    cursor.execute("CREATE TABLE if not exists contactus (name varchar(100) DEFAULT NULL,email varchar(100) DEFAULT NULL,message text)")
mydb=mysql.connector.connect(host=host,password=password,db=db,user=user,port=port)

@app.route('/')
def home():
    return render_template('welcome.html')

@app.route('/admincreate',methods=['GET','POST'])
def admincreate():
    if request.method=='POST':
        aname=request.form['username']
        aemail=request.form['email']
        password=request.form['password']
        address=request.form['address']
        accept=request.form['agree']
        print(request.form)
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(email) from admincreate where email=%s',[aemail]) 
            email_count=cursor.fetchone() #(0,)or(1,)
        except Exception as e:
            print(e)
            flash('connection error')
            return redirect(url_for('admincreate'))
        else:
            if email_count[0]==0:
                otp=genotp()
                admindata={'aname':aname,'aemail':aemail,'password':password,'address':address,'accept':accept,'aotp':otp}
                subject='Ecommerce verification code'
                body=f'Ecommerce otp for admin registration {otp}'
                sendmail(to=aemail,subject=subject,body=body)
                flash("otp has send to given mail")
                return redirect(url_for('aotp',paotp=encode(data=admindata)))
            elif email_count[0]==1:
                flash('Email already existed')
                return redirect(url_for('adminlogin'))
            else:
                flash('Wrong email')
                return redirect(url_for('admincreate'))
    return render_template('admincreate.html')

@app.route('/index')
def index():
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,price,quantity,category,image_name from items')
        items_data=cursor.fetchall()
    except Exception as e:
        print(e)
        flash("Could n't fetch items")
        return redirect(url_for('home'))
    return render_template('index.html',items_data=items_data)

    
@app.route('/aotp/<paotp>',methods=['GET','POST'])
def aotp(paotp):
    if request.method=='POST':
        fotp=request.form['otp']
        try:
            dotp=decode(data=paotp)
           # return 'abort error'
        except Exception as e:
            flash('something went wrong')
            return redirect(url_for('admincreate'))
        else:
            if dotp['aotp']==fotp:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into admincreate(email,username,password,address,accept) values(%s,%s,%s,%s,%s)',[dotp['aemail'],dotp['aname'],dotp['password'],dotp['address'],dotp['accept']])
                mydb.commit()
                cursor.close()
                flash("Admin Registration successfull")
                return redirect(url_for('adminlogin'))
            else:
                flash('otp was wrong')
                return redirect(url_for('aotp',paotp=paotp))    
    return render_template('adminotp.html')

@app.route('/adminlogin',methods=['GET','POST'])
def adminlogin():
    if not session.get('admin'):
        if request.method=='POST':
            aemail=request.form['email']
            password=request.form['password']
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select count(email) from admincreate where email=%s',[aemail])
                email_count=cursor.fetchone()
            except Exception as e:
                print(e)
                flash('connection  error')
                return redirect(url_for('adminlogin'))
            else:
                if email_count[0]==1:
                    cursor.execute('select password from admincreate where email=%s',[aemail])
                    stored_password=cursor.fetchone()
                    if stored_password[0].decode('utf-8')==password:
                        session['admin']=aemail             #here we are adding email to sessiion['admin']
                        if not session.get(aemail):
                            session[aemail]={}
                        return redirect(url_for('admindashboard'))
                    else:
                        flash('password was wrong')
                        return redirect(url_for('adminlogin'))
                elif email_count[0]==0:
                    flash('email was wrong')
                    return redirect(url_for('adminlogin'))
                else:
                    flash('email not registred')
                    return redirect(url_for('admincreate'))
        return render_template('adminlogin.html')
    else:
        return redirect(url_for('admindashboard'))
        
@app.route('/admindashboard')
def admindashboard():
    if session.get('admin'):
        return render_template('adminpanel.html')
    else:
        return redirect(url_for('adminlogin'))

@app.route('/adminforgot',methods=['GET','POST'])
def adminforgot():
    if request.method=='POST':
        forgot_email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(email) from admincreate where email=%s',[forgot_email])
        stored_email=cursor.fetchone()
        if stored_email[0]==1:
            subject='Admin password Reset link for Ecomee application'
            # body=f"Click on the link for password update:{encode(data=url_for('ad_password_update',_external=True))}"
            body=f"Click on the link for password update {url_for('ad_password_update',token=encode(data=forgot_email),_external=True)}:"
            sendmail(to=forgot_email,subject=subject,body=body)
            flash('Reset link has sent to given Email')
            return redirect(url_for('adminforgot'))
        elif stored_email[0]==0:
            flash('No email is registered Please check again')
            return redirect(url_for('adminforgot'))
    return render_template('forgot.html')

@app.route('/ad_password_update/<token>',methods=['GET','POST'])
def ad_password_update(token):
    if request.method=='POST':
        npassword=request.form['npassword']
        cpassword=request.form['cpassword']
        try:
            dtoken=decode(data=token)
        except Exception as e:
            print(e)
            flash('Email not found')
            return redirect(url_for('adminlogin'))
        else:
            if npassword==cpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update admincreate  set password=%s where email=%s',[npassword,dtoken])
                mydb.commit()
                flash('Password updated sucessfully')
                return redirect(url_for('adminlogin'))
            else:
                flash('Password Mismatch')
                return redirect(url_for('ad_password_update',token=token))
    return render_template('newpassword.html')

@app.route('/adminlogout')
def adminlogout():
    session.pop('admin')
    return redirect(url_for('adminlogin'))

@app.route('/additem',methods=['GET','POST'])
def additem():
    if session.get('admin'):
        if request.method=='POST':
            title=request.form['title']
            desc=request.form['Discription']
            price=request.form['price']
            category=request.form['category']
            quantity=request.form['quantity']
            item_img=request.files['file']
            filename=genotp()+'.'+item_img.filename.split('.')[-1]
            # print(filename)
            drname=os.path.dirname(os.path.abspath(__file__))       #
            print(drname)
            static_path=os.path.join(drname,'static')
            print(static_path)
            item_img.save(os.path.join(static_path,filename))        #the image will save on static files
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into items(item_id,item_name,price,quantity,category,image_name,added_by,description) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s,%s)',[title,price,quantity,category,filename,session.get('admin'),desc])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                flash('Connection Error')
                return redirect(url_for('additem'))
            else:
                flash(f'Item {title} added Successfully')
                return redirect(url_for('additem'))
        return render_template('additem.html')
    else:
        return redirect(url_for('adminlogin'))

@app.route('/viewallitems')
def viewallitems():
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(item_id),item_name,image_name from items where added_by=%s',[session.get('admin')])
            stored_itemdata=cursor.fetchall()
        except Exception as e:
            print(e)
            flash('Connection error')
            return redirect(url_for('adminpanel'))
        else:
            return render_template('viewall_items.html',stored_itemdata=stored_itemdata)
    else:
        return redirect(url_for('adminlogin'))

@app.route('/delete_item/<item_id>')
def delete_item(item_id):
    if session.get('admin'):
        try:
            drname=os.path.dirname(os.path.abspath(__file__))
            static_path=os.path.join(drname,'static')
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select image_name from items where item_id=uuid_to_bin(%s)',[item_id])
            stored_imgname=cursor.fetchone()
            print(stored_imgname)
            if stored_imgname in os.listdir(static_path):
                os.remove(os.path.join(static_path,stored_imgname[0]))
            cursor.execute('delete from items where item_id=uuid_to_bin(%s)',[item_id])
            mydb.commit()
        except Exception as e:
            print(e)
            flash("Couldn't delete item")
            return redirect(url_for('viewallitems'))
        else:
            flash('Deleted item successfully')
            return redirect(url_for('viewallitems'))
    else:
        return redirect(url_for('adminlogin'))

@app.route('/viewitem/<item_id>')
def viewitem(item_id):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(item_id),item_name,price,quantity,category,image_name,added_by,description from items where item_id=uuid_to_bin(%s)',[item_id])
            stored_itemdata=cursor.fetchone()
        except Exception as e:
            print(e)
            flash('Connection Problem')
            return redirect(url_for('viewallitems'))
        else:
            return render_template('view_item.html',data=stored_itemdata)
    else:
        return redirect(url_for('adminlogin'))

@app.route('/updateitem/<item_id>',methods=['GET','POST'])
def updateitem(item_id):
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select bin_to_uuid(item_id),item_name,price,quantity,category,image_name,added_by,description from items where item_id=uuid_to_bin(%s)',[item_id])
            stored_itemdata=cursor.fetchone()
        except Exception as e:
                print(e)
                flash('Connection Problem')
                return redirect(url_for('viewallitems'))
        else:
            if request.method=='POST':
                title=request.form['title']
                desc=request.form['Discription']
                price=request.form['price']
                category=request.form['category']
                quantity=request.form['quantity']
                item_img=request.files['file']
                filename=item_img.filename
                if filename== '':
                    img_name=stored_itemdata[5]
                else:
                    img_name=genotp()+'.'+filename.split('.')[-1]
                    drname=os.path.dirname(os.path.abspath(__file__))
                    static_path=os.path.join(drname,'static')
                    if stored_itemdata[5] in os.listdir(static_path):
                        os.remove(os.path.join(static_path,stored_itemdata[5]))
                    item_img.save(os.path.join(static_path,img_name))
                cursor.execute('update items set item_name=%s,price=%s,quantity=%s,category=%s,image_name=%s,description=%s where item_id=uuid_to_bin(%s)',[title,price,quantity,category,img_name,desc,item_id])
                mydb.commit()
                cursor.close()
                flash('item updated successfully')
                return redirect(url_for('viewitem',item_id=item_id))
        return render_template('update_item.html',stored_itemdata=stored_itemdata)
    else:
        return redirect(url_for('admin'))

@app.route('/adminupdate',methods=['GET','POST'])
def adminupdate():
    if session.get('admin'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select username,address,dp_image from admincreate where email=%s',[session.get('admin')]) #()
            admin_data=cursor.fetchone()
        except Exception as e:
            print(e)
            flash('connection problem')
            return redirect(url_for('adminpanel'))
        else:
            if request.method=='POST':
                username=request.form['adminname']
                dp_img=request.files['file']
                address=request.form['address']
                print(username,address,dp_img)
                if dp_img.filename=='':
                    img_name=admin_data[2]
                else:
                    img_name=genotp()+'.'+dp_img.filename.split('.')[-1] #new filename
                    drname=os.path.dirname(os.path.abspath(__file__)) #D:\CODE GNAN\FLASK\Ecommerce
                    static_path=os.path.join(drname,'static')
                    if admin_data[2] in os.listdir(static_path):
                        os.remove(os.path.join(static_path,admin_data[2]))
                    dp_img.save(os.path.join(static_path,img_name))
                cursor.execute('update admincreate set username=%s,address=%s,dp_image=%s where email=%s',[username,address,img_name,session.get('admin')])
                cursor.close()
                mydb.commit()
                flash('profile updated successfully') 
                return redirect(url_for('adminupdate'))           
        return render_template('adminupdate.html',admin_data=admin_data)
    else:
        return redirect(url_for('adminlogin'))

@app.route('/usersignup',methods=['GET','POST'])
def usersignup():
    if request.method=='POST':
        uname=request.form['name']
        uemail=request.form['email']
        password=request.form['password']
        address=request.form['address']
        gender=request.form['usergender']
        print(request.form) #accessing data from frontend as immutabledictionary format by name attribute
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(user_email) from usercreate where user_email=%s',[uemail])
            email_count=cursor.fetchone() #(0,) or (1,)
        except Exception as e:
            print(e)
            flash('Connection error')
            return redirect(url_for('usersignup'))
        else:
            if email_count[0]==0:
                otp=genotp()
                userdata={'uname':uname,'uemail':uemail,'password':password,'address':address,'gender':gender,'uotp':otp}
                subject='Ecommerce Verification Code'
                body=f'Ecommerce Otp For user Registration {otp}'
                sendmail(to=uemail,subject=subject,body=body)
                flash('Otp has sent to given mail')
                return redirect(url_for('uotp',puotp=encode(data=userdata)))# passing encrypt otp
            elif email_count[0]==1:
                flash('email already existed')
                return redirect(url_for('userlogin'))
            else:
                flash('wrong email')
                return redirect(url_for('usersignup'))
    return render_template('usersignup.html')

@app.route('/uotp<puotp>',methods=['GET','POST'])
def uotp(puotp):
    if request.method=='POST':
        fotp=request.form['otp']# user given otp
        try:
            dotp=decode(data=puotp) #decoding the encode otp
        except Exception as e:
            flash('something is wrong')
            return redirect(url_for('usersignup'))
        else:
            if dotp['uotp']==fotp:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into usercreate(user_email,username,password,address,gender)values(%s,%s,%s,%s,%s)',[dotp['uemail'],dotp['uname'],dotp['password'],dotp['address'],dotp['gender']])
                mydb.commit()
                cursor.close()
                flash('user registration successful')
                return redirect(url_for('userlogin'))
            else:
                flash('otp was worng')
                return redirect(url_for('uotp',puotp=puotp))
    return render_template('userotp.html')

@app.route('/userlogin',methods=['GET','POST'])
def userlogin():
    if not session.get('user'):
        if request.method=='POST':
            uemail=request.form['email']
            password=request.form['password']
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select count(user_email) from usercreate where user_email=%s',[uemail])
                email_count=cursor.fetchone()
            except Exception as e:
                print(e)
                flash('connection error')
                return redirect(url_for('userlogin'))
            else:
                if email_count[0]==1:
                    cursor.execute('select password from usercreate where user_email=%s',[uemail])
                    stored_password=cursor.fetchone()
                    if stored_password[0].decode('utf-8')==password:
                        session['user']=uemail
                        if not session.get(uemail):
                            session[uemail]={}
                        return redirect(url_for('index'))
                    else:
                        flash('password was wrong')
                        return redirect(url_for('userlogin'))
                elif email_count[0]==0:
                    flash('email was wrong')
                    return redirect(url_for('userlogin'))
                else:
                    flash('email not registred')
                    return redirect(url_for('usersignup'))
        return render_template('userlogin.html')
    else:
        return redirect(url_for('index'))

@app.route('/userforgot',methods=['GET','POST'])
def userforgot():
    if request.method=="POST":
        forgot_email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(user_email) from usercreate where user_email=%s',[forgot_email])
        stored_email=cursor.fetchone()
        if stored_email[0]==1:
            subject='user password reset link for ecommee application'
            body=f"click on the link for password updation: {url_for('user_password_update',token=encode(data=forgot_email),_external=True)}"
            sendmail(to=forgot_email,subject=subject,body=body)
            flash('Reset link has sent to given email')
            return redirect(url_for('userforgot'))
        elif stored_email[0]==0:
            flash('no email registered please check')
            return redirect(url_for('userforgot'))
    return render_template('forgot.html')

@app.route('/user_password_update/<token>',methods=['GET','POST'])
def user_password_update(token):
    if request.method=='POST':
        npassword=request.form['npassword']
        cpassword=request.form['cpassword']
        try:
            dtoken=decode(data=token)
        except Exception as e:
            print(e)
            flash('email not found')
            return redirect(url_for('userlogin'))
        else:
            if npassword==cpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update usercreate set password=%s where user_email=%s',[npassword,dtoken])
                mydb.commit()
                flash('password updated successfully')
                return redirect(url_for('userlogin'))
            else:
                flash('password mismatch')
                return redirect(url_for('user_password_update',token=token))    
    return render_template('newpassword.html')   

@app.route('/userlogout')
def userlogout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('userlogin'))
    return redirect(url_for('userlogin'))

@app.route('/category/<type>')
def category(type):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,price,quantity,category,image_name from items where category=%s',[type])
        items_data=cursor.fetchall()
    except Exception as e:
        print(e)
        flash("couln't fetch items")
        return redirect(url_for('index'))
    return render_template('dashboard.html',items_data=items_data)

@app.route('/addcart/<itemid>/<name>/<price>/<qyt>/<category>/<image>')

def addcart(itemid,name,price,qyt,category,image):
    if not session.get('user'):
        return redirect(url_for('userlogin'))
    else:
        print('session')
        if itemid not in session.get(session.get('user')):
            session.get(session.get('user'))[itemid]=[name,price,1,image,category,qyt]
            session.modified=True
            print(session)
            flash(f'item {name} added to cart')
            return redirect(url_for('index'))
        else:
            session[session.get('user')][itemid][2]+=1
            flash('Item already in cart')
            return redirect(url_for('index'))

@app.route('/viewcart')
def viewcart():
    if session.get('user'):
        if session.get(session.get('user')):
            items=session.get(session.get('user'))      #shows session data of loginemail
        else:
            items='empty'
        if items=='empty':
            flash('No items added in cart')
        return render_template('cart.html',items=items)
    else:
        return redirect(url_for('userlogin'))
        
@app.route('/removecart_item/<itemid>')
def removecart_item(itemid):
    if session.get('user'):
        session.get(session.get('user')).pop(itemid)
        session.modified=True
        flash('Item Removed From Cart')
        return redirect(url_for('viewcart'))
    else:
        return redirect(url_for('userlogin'))

@app.route('/description/<itemid>')
def description(itemid):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(item_id),item_name,description,price,quantity,category,image_name from items where item_id=uuid_to_bin(%s)',[itemid])
        item_data=cursor.fetchone()
    except Exception as e:
        print(e)
        flash("couln't fetch items")
        return redirect(url_for('index'))
    return render_template('description.html',item_data=item_data)

'''@app.route('/pay/<itemid>/<name>/<float:price>',methods=['GET','POST'])
def pay(itemid,name,price):
    if session.get('user'):
        try:
            qyt=int(request.form.get('qyt'))
            amount=price*100    #conevert price into paise
            total_price=qyt*amount
            print(f'creating payment for item:{itemid},name:{name},price:{total_price}')        ##create Razorpay order
            order=client.order.create({
                'amount':total_price,
                'currency':'INR',
                'payment_capture':'1'
            })
            print(f"order create:{order}")
            return render_template('pay.html',order=order,itemid=itemid,name=name,price=total_price,qyt=qyt)
        except Exception as e:
            #log the Error and return a 400 response
            print(f'Error creating order:{str(e)}')
            flash('Error creating order')
            return redirect(url_for('index'))
    else:
        return redirect(url_for('userlogin'))

@app.route('/success',methods=['POST'])
def success():
    if session.get('user'):
        #extract payment details from the form
        payment_id=request.form.get('razorpay_payment_id')
        order_id=request.form.get('razorpay_order_id')
        signature=request.form.get('razorpay_signature')
        name=request.form.get('name')
        itemid=request.form.get('itemid')
        total_price=request.form.get('total_price')
        qyt=request.form.get('qyt')
        #Verification Process
        params_dict={
            'razorpay_order_id':order_id,
            'razorpay_payment_id':payment_id,
            'razorpay_signature':signature
        }
        try:
            client.utility.verify_payment_signature(params_dict)
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into orders(itemid,item_name,total_price,user,qty) values(uuid_to_bin(%s),%s,%s,%s,%s)',[itemid,name,total_price,session.get('user'),qyt])
            mydb.commit()
            cursor.close()
        except razorpay.errors.SignatureVerificationError:
            return 'Payment Verification Failed',400
        else:
            flash('Order Placed Successfully')
            return 'Good Placed Order'
    else:
        return redirect(url_for('userlogin'))

@app.route('/orders')
def orders():
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select orderid,bin_to_uuid(itemid),item_name,total_price,qty,user from orders where user=%s',[session.get('user')])
            ordlist=cursor.fetchall()
        except Exception as e:
            print(f'Error in fetching orders:{e}')
            flash('Couldnt fetch orders')
            return redirect(url_for('index'))
        else:
            return render_template('orders.html',ordlist=ordlist)
    else:
        return redirect(url_for('userlogin'))'''

@app.route('/search',methods=['GET','POST'])
def search():
    if request.method=='POST':
        search=request.form['search']
        strg=['A-Za-z0-9']
        pattern=re.compile(f'^{strg}',re.IGNORECASE)
        if (pattern.match(search)):
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select bin_to_uuid(item_id),item_name,price,quantity,category,image_name,description from items where item_name like %s or price like %s or category like %s or description like %s',['%'+search+'%','%'+search+'%','%'+search+'%','%'+search+'%'])
                searched_data=cursor.fetchall()
            except Exception as e:
                print(f'Error in search{e}')
                flash('Could not fetch the data')
                return redirect(url_for('index'))
            else:
                return render_template('dashboard.html',items_data=searched_data)
        else:
            flash('No item found')
            return redirect(url_for('index'))
    return render_template('index.html')

@app.route('/addreview/<itemid>',methods=['GET','POST'])
def addreview(itemid):
    if session.get('user'):
        if request.method=='POST':
            title=request.form['title']
            reviewtext=request.form['review']
            rating=request.form['rate']
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into reviews(title,review,rating,itemid,username) values(%s,%s,%s,uuid_to_bin(%s),%s)',[title,reviewtext,rating,itemid,session.get('user')])
                mydb.commit()
            except Exception as e:
                print(f'Error in inserting review{e}')
                flash('cant add review')
                return redirect(url_for('description',itemid=itemid))
            else:
                cursor.close()
                flash('Review has been added')
                return redirect(url_for('description',itemid=itemid))
        return render_template('review.html')
    else:
        return redirect(url_for('userlogin'))

if __name__=='__main__':
    app.run(debug=True)