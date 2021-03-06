from collections import defaultdict
import concurrent.futures

import pandas as pd

from nflpicks import app, db
from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, login_required, logout_user
from nflpicks.models import User
from nflpicks.forms import LoginForm, RegistrationForm

from nflpicks.utils import get_games, get_winners, get_graphs, send_picks
from nflpicks.utils.logs import logging


@app.route('/')
def home():
    return render_template('home.html', completed=False)


@app.route('/games', methods=['GET', 'POST'])
@login_required
def index():

    # Get online and players data concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        games = executor.submit(get_games.GetGames,)
        points_ = executor.submit(get_winners.get_points,)

        games_data = games.result().round_games
        points = points_.result()

    # prepare data for json consumption
    query_data = games_data.to_dict(orient='records')
    games_count = games_data.shape[0]

    # Data from current user
    user_data = request.get_json()

    if user_data:
        logging.info(f'Current User {user_data["user"]}')

        user_df = defaultdict(list)
        for key, value in user_data['data'].items():
            user_df['winner'].append(value)
            losser = set(key.split('|')) - set([value])
            user_df['loser'].append(losser.pop())

        dt = pd.DataFrame(user_df)

        status = send_picks.send_to_db(dt, games_count, games_data, user_data)


        if status == 'incomplete':
            flash('Incomplete. You are missing some picks!')

    else:
        logging.info('No Data yet!')

    return render_template('index.html',
                           data=query_data,
                           points=points,
                           gamesCount=games_count)


@app.route('/completed', methods=['GET', 'POST'])
@login_required
def completed():
    logging.info('Complete Function: Completed')
    return render_template('home.html',
                            completed=True)

@app.route('/results', methods=['GET', 'POST'])
@login_required
def results():
    logging.info('Results called')
    data = get_winners.get_points_per_round()
    bar, points = get_graphs.get_results(data)
    
    return render_template('results.html', plot=bar, points=points)


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

        # User does not exist
        if user is None:
            flash(f'We have no record of user with {form.email.data}')

        if user and user.check_password(form.password.data):
            # Log in the user
            login_user(user)
            flash('Logged in successfully.')

            # If a user was trying to visit a page that requires a login
            next = request.args.get('next')

            if next is None or not next[0] == '/':
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
    app.run(host='0.0.0.0', debug=False, threaded=True)
