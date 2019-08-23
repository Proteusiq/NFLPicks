from collections import defaultdict
#from requests import Session
import pandas as pd


from nflpicks import app, db
from flask import render_template, redirect, request, url_for, flash, abort, jsonify
from flask_login import login_user,login_required,logout_user
from nflpicks.models import User
from nflpicks.forms import LoginForm, RegistrationForm
from werkzeug.security import generate_password_hash, check_password_hash



data = pd.read_json('nflpicks/data/fixtures.json', orient='records')

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/games', methods=['GET', 'POST'])
@app.route('/games/<int:round>', methods=['GET', 'POST'])
@login_required
def index(round=1):

	# Database
	mask = f'Round {round}'
	game_data = data[data['game_round'] == mask]
	query_data = game_data.to_dict(orient='records')

	games_count = game_data.shape[0]
	# Userbase

	user_data = request.get_json()

	if user_data:
		print('We got something ...')
		user_df = defaultdict(list)
		for key, value in user_data.items():
			#user_df['game'].append(key)
			user_df['winner'].append(value)
			losser = set(key.split('|')) - set([value])
			user_df['loser'].append(losser.pop())

		dt = pd.DataFrame(user_df)

		print(dt)
		if dt.shape[0] == games_count:
			print('True match completed')
			
		else:
			print('False match uncomplete')
			

	else:
		print('No Data yet!')
		

	return render_template('index.html', data=query_data, gamesCount=games_count)


@app.route('/completed', methods=['GET', 'POST'])
@login_required
def completed():
	print('Complete Function: Completed')
	return render_template('complete.html', data={'status': 'Completed'}, status=True)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You logged out!')
    return redirect(url_for('home'))


@app.route('/login', methods=['GET', 'POST'])
def login():

    form = LoginForm()
    if form.validate_on_submit():
        # Grab the user from our User Models table
        user = User.query.filter_by(email=form.email.data).first()

        if user.check_password(form.password.data) and user is not None:
            #Log in the user
            login_user(user)
            flash('Logged in successfully.')

            # If a user was trying to visit a page that requires a login
            next = request.args.get('next')

            if next is None or not next[0]=='/':
                next = url_for('index')

            return redirect(next)
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        user = User(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data)

        db.session.add(user)
        db.session.commit()
        flash('Thanks for registering! Now you can login!')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)
