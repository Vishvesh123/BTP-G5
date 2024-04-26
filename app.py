
from flask import Flask, render_template, request, redirect, session
import sys
import random
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

cosine_sim1 = pickle.load(open('similaritydiv2.pkl','rb'))
# cosine_sim2 = pickle.load(open('similaritydiv1.pkl','rb'))
svd = pickle.load(open("svd_model.pkl", "rb"))
df_movielens = pd.read_pickle("df_movielens.pkl")




# Create the SQLite database and tables
create_database()


def get_movie_id(movie_title, movies):
    movie_row = movies.loc[movies['title'] == movie_title]
    if not movie_row.empty:
        return movie_row.iloc[0]['movie_id']
    else:
        return None


# Fetch movie poster
def fetch_poster(movie_id):
    url = "https://api.themoviedb.org/3/movie/{}?api_key=5193a1b6768bfe00d7a6ec9caceda376&language=en-US".format(movie_id)
    data = requests.get(url)
    data = data.json()
    poster_path = data['poster_path']
    full_path = "https://image.tmdb.org/t/p/w500/" + poster_path
    return full_path

# Recommend movies
def recommendsearch(movie):
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
    return recommended_movie_details


def hybrid_recommendations(ratings, userId):
    all_movie_ids = []
    all_est_ratings = []
    all_movie_titles = []

    data_dict = {
        'userId': [rating.user_id for rating in ratings],
        'movieId': [rating.movie_id for rating in ratings],
        'title': [rating.movie_title for rating in ratings],
        'rating': [rating.rating for rating in ratings],
    }
    user_ratings = pd.DataFrame(data_dict)

    # Iterate over the rows and extract titles
    for index, row in user_ratings.iterrows():
        # Get the index of the movie that matches the title
        idx = movies[movies['title'] == row['title']].index
        idx = idx[0]

        # Get the pairwise similarity scores of all movies with that movie
        sim_scores = list(enumerate(cosine_sim1[idx]))

        # Sort the movies based on the similarity scores
        sim_scores.sort(key=lambda x: x[1], reverse=True)

        # Get the scores of the 10 most similar movies
        sim_scores = sim_scores[1:11]

        # Get the movie indices
        ind = []
        for (x, y) in sim_scores:
            ind.append(x)

        # Grab the movieId of the top 10 most similar movies
        tit = []
        movieids = []
        for x in ind:
            tit.append(df_movielens.iloc[x]['title'])
            movieids.append(df_movielens.iloc[x]['movieId'])

        # Predict the ratings a user might give to these top 10 most similar movies
        est_ratings = []
        for movie_id in movieids:
            est_ratings.append(svd.predict(userId, movie_id, r_ui=None).est)

        all_movie_ids.extend(movieids)
        all_est_ratings.extend(est_ratings)
        all_movie_titles.extend(tit)

    # Create the DataFrame with equal-length lists
    df = pd.DataFrame({'index': range(len(all_movie_titles)), 'title': all_movie_titles, 'movieId': all_movie_ids, 'estimated_rating': all_est_ratings}).set_index('index').sort_values(by='estimated_rating', ascending=False)

    # Shuffle the DataFrame rows
    df = df.sample(frac=1).reset_index(drop=True)

    recommended_movie_posters = []
    recommended_movies = []
    seen_movies = set()
    seen_posters = set()

    # Iterate over the shuffled rows and extract movie IDs and titles
    for index, row in df.iterrows():
        movie_id = row['movieId']
        movie_title = row['title']
        poster_url = fetch_poster(movie_id)

        # Skip movies and posters that have already been recommended
        if movie_title in seen_movies or poster_url in seen_posters:
            continue

        seen_movies.add(movie_title)
        seen_posters.add(poster_url)

        recommended_movie_posters.append(poster_url)
        recommended_movies.append(movie_title)

        # Break the loop after 4-5 unique recommendations
        if len(recommended_movies) >= 6:
            break

    return recommended_movies, recommended_movie_posters

def recommend(titles, cosine_sim):
    all_recommended_movies = []
    all_recommended_movie_posters = []
    all_sim_scores = []

    for title in titles:
        # Get the index of the movie that matches the title
        movie_index = movies[movies['title'] == title].index
        if not movie_index.empty:
            movie_index = movie_index[0]

            # Get the pairwise similarity scores of all movies with that movie
            sim_scores = list(enumerate(cosine_sim[movie_index]))

            # Sort the movies based on the similarity scores
            sim_scores.sort(key=lambda x: x[1], reverse=True)

            # Get the indices of the top 6 most similar movies (excluding the input movie itself)
            movie_indices = [x[0] for x in sim_scores[1:10]]

            # Get the movie IDs, titles, and posters of the recommended movies
            recommended_movies = []
            recommended_movie_posters = []
            for idx in movie_indices:
                movie_id = movies.iloc[idx].movie_id
                movie_title = movies.iloc[idx].title
                poster_url = fetch_poster(movie_id)
                recommended_movies.append(movie_title)
                recommended_movie_posters.append(poster_url)

            all_recommended_movies.extend(recommended_movies)
            all_recommended_movie_posters.extend(recommended_movie_posters)
            all_sim_scores.extend([score[1] for score in sim_scores[1:10]])

    # Sort the combined list of recommended movies based on similarity scores
    combined_recommendations = sorted(zip(all_recommended_movies, all_recommended_movie_posters, all_sim_scores), key=lambda x: x[2], reverse=True)
     # Get the top 6-7 most similar movies
    # top_movies = [rec[0] for rec in combined_recommendations[:11]]
    # top_movie_posters = [rec[1] for rec in combined_recommendations[:11]]

    # return top_movies, top_movie_posters
    

    # Shuffle the combined list

    random.shuffle(combined_recommendations)
    # return top_movies, top_movie_posters
    random.shuffle(combined_recommendations)

    # Extract unique titles and poster URLs while maintaining alignment
    unique_movies = []
    unique_posters = []
    seen_titles = set()
    for rec in combined_recommendations:
        movie_title, poster_url, _ = rec
        if movie_title not in seen_titles:
            seen_titles.add(movie_title)
            unique_movies.append(movie_title)
            unique_posters.append(poster_url)

    # Randomly select a subset of unique recommendations
    num_recommendations = min(len(unique_movies), 6)
    random_indices = random.sample(range(len(unique_movies)), num_recommendations)
    random_movies = [unique_movies[i] for i in random_indices]
    random_posters = [unique_posters[i] for i in random_indices]

    return random_movies, random_posters



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



@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/login')

    engine = create_database()
    Session = sessionmaker(bind=engine)
    db_session = Session()
    user = db_session.query(User).filter_by(username=session['user']).first()
    search_histories = db_session.query(SearchHistory).filter_by(user_id=user.id).all()
    db_session.close()

    return render_template('history.html', search_history=search_histories, user=user.username)

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

@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'user' not in session:
         return redirect('/login')

    if request.method == 'POST':
       
        selected_movie_name = request.form['movie']
        movie_id = int(get_movie_id(selected_movie_name, movies))
        if session and 'user' in session and create_database and User and SearchHistory:
                engine = create_database()
                Session = sessionmaker(bind=engine)
                db_session = Session()
                user = db_session.query(User).filter_by(username=session['user']).first()
                if movie_id:
                    print(f"Storing movie_id: {movie_id} for movie: {selected_movie_name}", file=sys.stdout)
                    search_history = SearchHistory(user_id=user.id, movie_id=movie_id, movie_title=selected_movie_name)
                    db_session.add(search_history)
                    db_session.commit()
                else:
                    print(f"Movie '{selected_movie_name}' not found in the database.", file=sys.stdout)
                db_session.close()
        else:
            print(f"Movie '{selected_movie_name}' not found in the database.", file=sys.stdout)
        
        if 'movie' in request.form:
            recommended_movie_details = recommendsearch(selected_movie_name)
            return render_template('search.html', movies=movies['title'].values, user=session['user'],
                                   recommended_movie_details=recommended_movie_details)
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

    return render_template('search.html', movies=movies['title'].values, user=session['user'])
        





@app.route('/', methods=['GET', 'POST'])
def home():
    if 'user' not in session:
        return redirect('/login')
    # Query the search history for the current user
    engine = create_database()
    Session = sessionmaker(bind=engine)
    db_session = Session()
    user = db_session.query(User).filter_by(username=session['user']).first()
    titles=[]
    search_histories = db_session.query(SearchHistory).filter_by(user_id=user.id).all()
    ratings = db_session.query(UserRating).filter_by(user_id=user.id).all()
    if search_histories:
            titles = [history.movie_title for history in search_histories]
    db_session.close()

    if ratings :
      recommended_movie_names, recommended_movie_posters = hybrid_recommendations(ratings,user.id)
      print('hybrid')
      return render_template('index.html', movies=movies['title'].values, user=session['user'],
                               recommended_movies=zip(recommended_movie_names, recommended_movie_posters),
                               search_history=search_histories)  
        
      
    # return render_template('index.html', movies=movies['title'].values, user=session['user'], search_history=search_histories)
    recommended_movie_names, recommended_movie_posters = recommend(titles,cosine_sim1)
    if recommended_movie_names and recommended_movie_posters :
     return render_template('index.html', movies=movies['title'].values, user=session['user'],
                               recommended_movies=zip(recommended_movie_names, recommended_movie_posters),
                               search_history=search_histories)
    else :
        return render_template('index.html', movies=movies['title'].values, user=session['user'], search_history=search_histories)






if __name__ == '__main__':
    create_database()
    app.run(debug=True)

