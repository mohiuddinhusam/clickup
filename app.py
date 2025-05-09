from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_pymongo import PyMongo
from models import User
from werkzeug.utils import secure_filename
from datetime import datetime
from bson.objectid import ObjectId
from urllib.parse import quote_plus
import os
import random
import string
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary
import cloudinary.uploader



clickup_app = Flask(__name__)


clickup_app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
clickup_app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
clickup_app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


load_dotenv()  # Load environment variables from .env file

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET")
)

VALID_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm'}


auth_manager = LoginManager()
auth_manager.init_app(clickup_app)
auth_manager.login_view = 'login'


db_client = None
try:
    
    username = quote_plus(os.getenv("DB_USERNAME"))
    password = quote_plus(os.getenv("DB_PASSWORD"))
    db_name = os.getenv("DB_NAME")
    
    clickup_app.config['MONGO_URI'] = f"mongodb+srv://{username}:{password}@cluster0.icb0jjr.mongodb.net/{db_name}?retryWrites=true&w=majority"

    
    db_client = PyMongo(clickup_app)
    db_client.db.command('ping')
    print("MongoDB Atlas connection successful!")
    
except Exception as e:
    print(f"MongoDB Atlas connection error: {e}")
    print("Attempting alternative connection...")
    
    try:
        from pymongo import MongoClient
        
        connection_string = f"mongodb+srv://{username}:{password}@clickup.sxqrqch.mongodb.net/clickup_db?retryWrites=true&w=majority"
        client = MongoClient(connection_string, 
                             ssl=True, 
                             tlsAllowInvalidCertificates=True)
        
        
        db = client.clickup_db
        db.command('ping')
        print("Alternative connection method successful!")
        
        
        class MongoClientWrapper:
            def __init__(self, database):
                self.db = database
                
        db_client = MongoClientWrapper(db)
        
    except Exception as alt_e:
        print(f"Alternative connection failed: {alt_e}")
        db_client = None


@clickup_app.template_filter('timesince')
def format_time_elapsed(dt):
    """Format a datetime as relative time (e.g., "4 hours ago")."""
    now = datetime.utcnow()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return 'just now'
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f'{minutes} {"minute" if minutes == 1 else "minutes"} ago'
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f'{hours} {"hour" if hours == 1 else "hours"} ago'
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f'{days} {"day" if days == 1 else "days"} ago'
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f'{weeks} {"week" if weeks == 1 else "weeks"} ago'
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f'{months} {"month" if months == 1 else "months"} ago'
    else:
        years = int(seconds / 31536000)
        return f'{years} {"year" if years == 1 else "years"} ago'


@auth_manager.user_loader
def fetch_user_by_id(user_id):
    try:
        if db_client is None:
            print("Database connection unavailable")
            return None
            
        user_data = db_client.db.users.find_one({'_id': ObjectId(user_id)})
        
        if user_data:
            print(f"User loaded: {user_data['username']}")
            return User(user_data)
        else:
            print(f"User not found with ID: {user_id}")
            return None
    except Exception as e:
        print(f"User loading error: {str(e)}")
        return None


def validate_file_extension(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in VALID_EXTENSIONS


def create_unique_filename(original_filename):
    """Generate a unique filename while preserving the original extension."""
    ext = original_filename.rsplit('.', 1)[1].lower()
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{timestamp}_{random_string}.{ext}"


def remove_cloudinary_asset(public_id):
    """Remove a video from Cloudinary storage."""
    try:
        cloudinary.uploader.destroy(public_id, resource_type="video")
    except Exception as e:
        print(f"Cloudinary deletion error: {str(e)}")


def prepare_database_collections():
    """Prepare and configure database collections."""
    try:
        if db_client is None:
            print("Database connection unavailable")
            return
            
        collections = db_client.db.list_collection_names()
        
        
        if 'users' not in collections:
            db_client.db.create_collection('users')
            print("Users collection created")
            
        if 'videos' not in collections:
            db_client.db.create_collection('videos')
            print("Videos collection created")
            
        
        db_client.db.videos.create_index([('created_at', -1)])
        db_client.db.videos.create_index([('user_id', 1)])
        db_client.db.users.create_index([('username', 1)])
        print("Database indexes created")
    except Exception as e:
        print(f"Collection initialization error: {str(e)}")


@clickup_app.route('/health')
def system_health_check():
    """Endpoint to check system health status."""
    status = {
        'app': 'OK',
        'mongodb': 'Not Connected'
    }
    
    try:
        if db_client is not None:
            if hasattr(db_client, 'db'):
                db_client.db.command('ping')
                status['mongodb'] = 'Connected (Flask-PyMongo)'
            else:
                db_client.db.command('ping')
                status['mongodb'] = 'Connected (MongoClient)'
                
            status['database_info'] = {
                'collections': db_client.db.list_collection_names() if hasattr(db_client.db, 'list_collection_names') else [],
                'users_count': db_client.db.users.count_documents({}) if hasattr(db_client.db.users, 'count_documents') else 0
            }
    except Exception as e:
        status['mongodb'] = f'Error: {str(e)}'
        status['error_details'] = str(e.__class__.__name__)
    
    return jsonify(status)


@clickup_app.route('/create_account', methods=['POST'])
def create_user_account():
    """Create a new user account."""
    if db_client is None:
        return jsonify({'error': 'Database connection is unavailable'}), 500
    
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ['username', 'password', 'role']):
            return jsonify({'error': 'Missing required fields'}), 400
            
        if db_client.db.users.find_one({'username': data['username']}):
            return jsonify({'error': 'Username already exists'}), 400
            
        user = {
            'username': data['username'],
            'password': generate_password_hash(data['password']),
            'role': data['role'],
            'avatar_url': '',
            'bio': '',
            'created_at': datetime.utcnow()
        }
        
        result = db_client.db.users.insert_one(user)
        
        if result.inserted_id:
            print(f"User account created: {result.inserted_id}")
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Account creation failed'}), 500
            
    except Exception as e:
        print(f"Account creation error: {str(e)}")
        return jsonify({'error': 'Failed to create account'}), 500


@clickup_app.route('/auth_user', methods=['POST'])
def authenticate_user():
    """Authenticate a user and create a session."""
    if db_client is None:
        return jsonify({'error': 'Database connection is unavailable'}), 500
    
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ['username', 'password']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        user_data = db_client.db.users.find_one({'username': data['username']})
        
        if user_data and check_password_hash(user_data['password'], data['password']):
            user = User(user_data)
            login_user(user)
            
            print(f"User authenticated: {user.username}, role: {user.role}")
            
            return jsonify({
                'success': True, 
                'role': user_data['role'],
                'username': user_data['username'],
                'user_id': str(user_data['_id'])
            })
        
        return jsonify({'error': 'Invalid username or password'}), 401
        
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        return jsonify({'error': 'Authentication failed'}), 500


@clickup_app.route('/end_session')
@login_required
def end_user_session():
    """End the user's session."""
    try:
        logout_user()
        return jsonify({'success': True, 'message': 'Session ended successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@clickup_app.route('/')
def content_feed():
    """Display the main content feed."""
    try:
        if db_client is None:
            print("Database connection unavailable")
            return render_template('home.html', videos=[], page=1, total_pages=1, error="Database connection error")
        
        search_query = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = 10

        query = {}
        if search_query:
            query = {
                '$or': [
                    {'title': {'$regex': search_query, '$options': 'i'}},
                    {'description': {'$regex': search_query, '$options': 'i'}},
                    {'username': {'$regex': search_query, '$options': 'i'}}
                ]
            }
            
        
        total_videos = db_client.db.videos.count_documents(query)

        
        videos = list(
            db_client.db.videos.find(query)
            .sort('created_at', -1)
            .skip((page - 1) * per_page)
            .limit(per_page)
        )

        
        for video in videos:
            video['_id'] = str(video['_id'])
            video['user_id'] = str(video['user_id'])
            video['likes'] = [str(like) for like in video.get('likes', [])]

        total_pages = (total_videos + per_page - 1) // per_page if total_videos > 0 else 1

        return render_template(
            'home.html',
            videos=videos,
            page=page,
            total_pages=total_pages,
            search_query=search_query
        )
    except Exception as e:
        print(f"Content feed error: {str(e)}")
        return render_template('home.html', videos=[], page=1, total_pages=1, error=f"An error occurred: {str(e)}")


@clickup_app.route('/publish_content', methods=['GET', 'POST'])
@login_required
def publish_new_content():
    """Publish new video content."""
    
    if current_user.role != 'creator':
        return redirect(url_for('content_feed'))
        
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                print("No file in request")
                return jsonify({'error': 'No video file uploaded'}), 400
            
            video = request.files['file']
            if video.filename == '':
                print("Empty filename")
                return jsonify({'error': 'No selected file'}), 400

            print(f"Processing upload: {video.filename}")
            
            
            upload_result = cloudinary.uploader.upload(
                video,
                resource_type="video",
                folder="ClickUp_videos",
                chunk_size=6000000
            )

            print(f"Upload complete: {upload_result}")

            
            video_data = {
                'title': request.form.get('title', ''),
                'description': request.form.get('description', ''),
                'video_url': upload_result['secure_url'],
                'public_id': upload_result['public_id'],
                'user_id': ObjectId(current_user.id),
                'username': current_user.username,
                'created_at': datetime.utcnow(),
                'likes': [],
                'views': 0,
                'comments': []
            }
            
            result = db_client.db.videos.insert_one(video_data)
            print(f"Content published: {result.inserted_id}")
            
            return jsonify({'success': True, 'message': 'Content published successfully!'})

        except Exception as e:
            print(f"Publishing error: {str(e)}")
            return jsonify({'error': str(e)}), 500

    return render_template('uploadvideo.html')


@clickup_app.route('/user_profile', methods=['GET'])
@login_required
def view_user_profile():
    """View the current user's profile."""
    try:
        # Get the user's videos
        user_videos = list(db_client.db.videos.find({'user_id': ObjectId(current_user.id)}).sort('created_at', -1))
        for video in user_videos:
            video['_id'] = str(video['_id'])
            video['likes'] = len(video.get('likes', []))
        
        # Get videos liked by the user
        user_id = ObjectId(current_user.id)
        liked_videos = list(db_client.db.videos.find({'likes': user_id}).sort('created_at', -1))
        for video in liked_videos:
            video['_id'] = str(video['_id'])
            video['user_id'] = str(video['user_id'])
            video['likes'] = len(video.get('likes', []))
        
        return render_template('myprofile.html', user=current_user, videos=user_videos, liked_videos=liked_videos)
    except Exception as e:
        print(f"Profile error: {str(e)}")
        return redirect(url_for('content_feed'))


@clickup_app.route('/update_user_profile', methods=['POST'])
@login_required
def update_user_profile():
    """Update user profile information."""
    try:
        data = request.get_json()
        update_data = {
            'username': data.get('username', current_user.username),
            'bio': data.get('bio', ''),
            'avatar_url': data.get('avatar_url', '')
        }
        
        db_client.db.users.update_one(
            {'_id': ObjectId(current_user.id)},
            {'$set': update_data}
        )
        
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@clickup_app.route('/remove_content/<video_id>', methods=['POST'])
@login_required
def remove_user_content(video_id):
    """Remove a user's video content."""
    try:
        video = db_client.db.videos.find_one({'_id': ObjectId(video_id)})
        
        if video and str(video['user_id']) == current_user.id:
            
            cloudinary.uploader.destroy(video['public_id'], resource_type="video")
            
            
            db_client.db.videos.delete_one({'_id': ObjectId(video_id)})
            
            return jsonify({'success': True, 'message': 'Content removed successfully'})
            
        return jsonify({'error': 'Content not found or unauthorized'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@clickup_app.route('/toggle_reaction/<video_id>', methods=['POST'])
@login_required
def toggle_content_reaction(video_id):
    """Toggle a like/reaction on a video."""
    try:
        user_id = ObjectId(current_user.id)
        video = db_client.db.videos.find_one({'_id': ObjectId(video_id)})
        
        if not video:
            return jsonify({'error': 'Content not found'}), 404
            
        likes = video.get('likes', [])
        likes = [str(like) for like in likes]  
        
        if str(user_id) in likes:
            
            db_client.db.videos.update_one(
                {'_id': ObjectId(video_id)},
                {'$pull': {'likes': user_id}}
            )
        else:
            
            db_client.db.videos.update_one(
                {'_id': ObjectId(video_id)},
                {'$addToSet': {'likes': user_id}}
            )
            
        updated_video = db_client.db.videos.find_one({'_id': ObjectId(video_id)})
        return jsonify({
            'likes': len(updated_video.get('likes', [])),
            'is_liked': str(user_id) in [str(like) for like in updated_video.get('likes', [])]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@clickup_app.route('/discussions/<video_id>', methods=['GET'])
def fetch_content_discussions(video_id):
    """Fetch comments for a specific video."""
    try:
        video = db_client.db.videos.find_one({'_id': ObjectId(video_id)})
        if not video:
            return jsonify({'error': 'Content not found'}), 404

        comments = video.get('comments', [])
        return jsonify({'comments': comments})
    except Exception as e:
        print(f"Error fetching discussions: {str(e)}")
        return jsonify({'error': str(e)}), 500


@clickup_app.route('/add_discussion/<video_id>', methods=['POST'])
@login_required
def add_content_discussion(video_id):
    """Add a comment to a video."""
    try:
        data = request.get_json()
        comment_text = data.get('comment')

        if not comment_text:
            return jsonify({'error': 'Comment text is required'}), 400

        comment = {
            'user_id': str(current_user.id),
            'username': current_user.username,
            'text': comment_text,
            'timestamp': datetime.utcnow().isoformat()
        }

        result = db_client.db.videos.update_one(
            {'_id': ObjectId(video_id)},
            {'$push': {'comments': comment}}
        )

        if result.modified_count == 0:
            return jsonify({'error': 'Content not found'}), 404

        return jsonify({'success': True, 'comment': comment})
    except Exception as e:
        print(f"Error adding discussion: {str(e)}")
        return jsonify({'error': str(e)}), 500


@clickup_app.route('/update_profile_image', methods=['POST'])
@login_required
def update_profile_image():
    """Update the user's profile avatar."""
    try:
        if 'avatar' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        avatar = request.files['avatar']
        
        if avatar.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if avatar:
            upload_result = cloudinary.uploader.upload(
                avatar,
                folder="ClickUp_avatars"
            )
            
            avatar_url = upload_result['secure_url']
            
            db_client.db.users.update_one(
                {'_id': ObjectId(current_user.id)},
                {'$set': {'avatar_url': avatar_url}}
            )
            
            return jsonify({'success': True, 'avatar_url': avatar_url})
            
    except Exception as e:
        print(f"Profile image update error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@clickup_app.teardown_appcontext
def release_resources(exception=None):
    """Release any resources when the application context ends."""
    pass




@clickup_app.route('/signup', methods=['POST'])
def signup():
    return create_user_account()

@clickup_app.route('/login', methods=['POST'])
def login():
    return authenticate_user()

@clickup_app.route('/logout')
def logout():
    return end_user_session()

@clickup_app.route('/profile')
def profile():
    return view_user_profile()

@clickup_app.route('/upload', methods=['GET', 'POST'])
def upload():
    return publish_new_content()

@clickup_app.route('/update_profile', methods=['POST'])
def update_profile():
    return update_user_profile()

@clickup_app.route('/delete_video/<video_id>', methods=['POST'])
def delete_video(video_id):
    return remove_user_content(video_id)

@clickup_app.route('/like/<video_id>', methods=['POST'])
def like_video(video_id):
    return toggle_content_reaction(video_id)

@clickup_app.route('/comments/<video_id>')
def get_comments(video_id):
    return fetch_content_discussions(video_id)

@clickup_app.route('/comment/<video_id>', methods=['POST'])
def add_comment(video_id):
    return add_content_discussion(video_id)

@clickup_app.route('/update_avatar', methods=['POST'])
def update_avatar():
    return update_profile_image()


@clickup_app.route('/user_liked_videos')
@login_required
def get_user_liked_videos():
    """Get videos that the current user has liked."""
    try:
        # Find all videos where current user's ID is in the likes array
        user_id = ObjectId(current_user.id)
        liked_videos = list(db_client.db.videos.find({'likes': user_id}).sort('created_at', -1))
        
        # Format for frontend consumption
        for video in liked_videos:
            video['_id'] = str(video['_id'])
            video['user_id'] = str(video['user_id'])
            video['likes'] = len(video.get('likes', []))
        
        return jsonify({'success': True, 'videos': liked_videos})
    except Exception as e:
        print(f"Error fetching liked videos: {str(e)}")
        return jsonify({'error': str(e)}), 500


@clickup_app.route('/liked_videos')
def liked_videos():
    """Alias for get_user_liked_videos"""
    return get_user_liked_videos()


if __name__ == '__main__':
    if db_client is not None:
        prepare_database_collections()
    clickup_app.run(debug=True)
