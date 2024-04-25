
from flask import Flask, render_template, request, redirect, session
import pickle
import pandas as pd
import requests
from sqlalchemy.orm import sessionmaker
from database import User, SearchHistory,UserRating, create_database, add_user, get_user

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Load the movie data and similarity matrix
movies_dict = pickle.load(open('movie_dict.pkl', 'rb'))
similarity = pickle.load(open('similarity.pkl', 'rb'))
movies = pd.DataFrame(movies_dict)

# Create the SQLite database and tables
create_database()

# Fetch movie poster
def fetch_poster(movie_id):
    url = "https://api.themoviedb.org/3/movie/{}?api_key=5193a1b6768bfe00d7a6ec9caceda376&language=en-US".format(movie_id)
    data = requests.get(url)
    data = data.json()
    poster_path = data['poster_path']
    full_path = "https://image.tmdb.org/t/p/w500/" + poster_path
    return full_path

# # Recommend movies
# def recommend(movie):
#     movie_index = movies[movies['title'] == movie].index[0]
#     movie_list = sorted(list(enumerate(similarity[movie_index])), reverse=True, key=lambda x: x[1])[1:7]
#     recommended_movies = []
#     recommended_movie_posters = []
#     for i in movie_list:
#         movie_id = movies.iloc[i[0]].movie_id
#         recommended_movie_posters.append(fetch_poster(movie_id))
#         recommended_movies.append(movies.iloc[i[0]].title)

#     # Save search history
#     if 'user' in session:
#         engine = create_database()
#         Session = sessionmaker(bind=engine)
#         db_session = Session()
#         user = db_session.query(User).filter_by(username=session['user']).first()  
#         search_history = SearchHistory(user_id=user.id, movie_id=int(movies.iloc[movie_index].movie_id), movie_title=movie)
#         print(movies.iloc[movie_index])
#         print("hellooooooooo")
#         db_session.add(search_history)
#         db_session.commit()
#         db_session.close()

        

#     return recommended_movies, recommended_movie_posters


def recommend(movie):
    movie_index = movies[movies['title'] == movie].index[0]
    movie_list = sorted(list(enumerate(similarity[movie_index])), reverse=True, key=lambda x: x[1])[1:7]
    recommended_movie_details = []
    for i in movie_list:
        movie_id = movies.iloc[i[0]].movie_id
        movie_title = movies.iloc[i[0]].title
        movie_poster = fetch_poster(movie_id)
        recommended_movie_details.append({
            'movie_id': movie_id,
            'title': movie_title,
            'poster': movie_poster
        })

    # Save search history
    if 'user' in session:
        engine = create_database()
        Session = sessionmaker(bind=engine)
        db_session = Session()
        user = db_session.query(User).filter_by(username=session['user']).first()  
        search_history = SearchHistory(user_id=user.id, movie_id=int(movies.iloc[movie_index].movie_id), movie_title=movie)
        db_session.add(search_history)
        db_session.commit()
        db_session.close()

    return recommended_movie_details


# Login and registration routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user(username)
        if user and user.password == password:
            session['user'] = user.username
            return redirect('/')
        else:
            return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        username = request.form['username']
        password = request.form['password']
        try:
            add_user(fullname, username, password)
            user = get_user(username)
            session['user'] = user.username
            return redirect('/')
        except Exception as e:
            return render_template('register.html', error=str(e))
    return render_template('register.html')




@app.route('/rate', methods=['POST'])
def rate_movie():
    if 'user' not in session:
        return 'Not logged in', 401

    movie_id = int(request.form.get('movie_id'))
    movie_title = request.form.get('movie_title')
    rating = int(request.form.get('rating'))

    # Save user rating
    engine = create_database()
    Session = sessionmaker(bind=engine)
    db_session = Session()
    user = db_session.query(User).filter_by(username=session['user']).first()
    user_rating = UserRating(user_id=user.id, movie_id=movie_id, movie_title=movie_title, rating=rating)
    db_session.add(user_rating)
    db_session.commit()
    db_session.close()

    return 'Rating saved successfully'



@app.route('/', methods=['GET', 'POST'])
def home():
    if 'user' not in session:
        return redirect('/login')

    engine = create_database()
    Session = sessionmaker(bind=engine)
    db_session = Session()
    user = db_session.query(User).filter_by(username=session['user']).first()
    search_history = db_session.query(SearchHistory).filter_by(user_id=user.id).all()
    db_session.close()

    if request.method == 'POST':
        if 'movie' in request.form:
            selected_movie_name = request.form['movie']
            recommended_movie_details = recommend(selected_movie_name)
            return render_template('index.html', movies=movies['title'].values, user=session['user'],
                                   recommended_movie_details=recommended_movie_details,
                                   search_history=search_history)
        elif 'rating' in request.form:
            movie_id_str = request.form.get('movie_id')
            if movie_id_str:
                movie_id = int(movie_id_str)
                movie_title = request.form['movie_title']
                rating = int(request.form['rating'])

                # Save user rating
                engine = create_database()
                Session = sessionmaker(bind=engine)
                db_session = Session()
                user = db_session.query(User).filter_by(username=session['user']).first()
                user_rating = UserRating(user_id=user.id, movie_id=movie_id, movie_title=movie_title, rating=rating)
                db_session.add(user_rating)
                db_session.commit()
                db_session.close()

    return render_template('index.html', movies=movies['title'].values, user=session['user'], search_history=search_history)


if __name__ == '__main__':
    create_database()
    app.run(debug=True)


