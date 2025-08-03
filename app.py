from flask import Flask, render_template, request, redirect, session, url_for
import yaml

app = Flask(__name__)
app.secret_key = 'offline-first-key'

with open('data/users.yaml') as f:
    USERS = yaml.safe_load(f)['users']

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pword = request.form['password']
        for user in USERS:
            if user['username'] == uname and user['password'] == pword:
                session['user'] = uname
                return redirect('/home')
        return "Invalid credentials", 401
    return render_template('login.html')

@app.route('/home')
def home():
    if 'user' not in session:
        return redirect('/')
    return render_template('home.html', user=session['user'])

if __name__ == '__main__':
    app.run(debug=True)
