
import os
import logging
from app import app, db
from models import User, Player, Tournament, Round, RoundPairing, TournamentPlayer, Match
import psycopg2
import psycopg2.extras

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_data():
    # Get PostgreSQL connection details from environment
    postgres_url = os.environ.get("DATABASE_URL")
    
    if not postgres_url:
        logger.error("No PostgreSQL DATABASE_URL found in environment variables")
        return False
    
    try:
        # Connect to PostgreSQL
        logger.info("Connecting to PostgreSQL database...")
        conn = psycopg2.connect(postgres_url)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        with app.app_context():
            # Create SQLite tables
            logger.info("Creating SQLite tables...")
            db.create_all()
            
            # Migrate Users
            logger.info("Migrating Users...")
            cursor.execute("SELECT id, username, email, password_hash, is_admin FROM \"user\"")
            users = cursor.fetchall()
            for user in users:
                new_user = User(
                    id=user['id'],
                    username=user['username'],
                    email=user['email'],
                    password_hash=user['password_hash'],
                    is_admin=user['is_admin']
                )
                db.session.add(new_user)
            
            # Migrate Players
            logger.info("Migrating Players...")
            cursor.execute("SELECT * FROM player")
            players = cursor.fetchall()
            for player in players:
                new_player = Player(
                    id=player['id'],
                    player_id=player['player_id'],
                    first_name=player['first_name'],
                    middle_name=player['middle_name'],
                    last_name=player['last_name'],
                    state=player['state'],
                    email=player['email'],
                    phone=player['phone'],
                    id_card_photo=player['id_card_photo'],
                    player_photo=player['player_photo'],
                    rating=player['rating'],
                    rating_deviation=player['rating_deviation'],
                    volatility=player['volatility'],
                    last_active=player['last_active']
                )
                db.session.add(new_player)
            
            # Migrate Tournaments
            logger.info("Migrating Tournaments...")
            cursor.execute("SELECT * FROM tournament")
            tournaments = cursor.fetchall()
            for tournament in tournaments:
                new_tournament = Tournament(
                    id=tournament['id'],
                    tournament_id=tournament['tournament_id'],
                    name=tournament['name'],
                    start_date=tournament['start_date'],
                    end_date=tournament['end_date'],
                    state=tournament['state'],
                    info=tournament['info'],
                    cover_photo=tournament['cover_photo'],
                    status=tournament['status'],
                    pairing_system=tournament['pairing_system']
                )
                db.session.add(new_tournament)
            
            # Migrate Rounds
            logger.info("Migrating Rounds...")
            cursor.execute("SELECT * FROM round")
            rounds = cursor.fetchall()
            for round_data in rounds:
                new_round = Round(
                    id=round_data['id'],
                    tournament_id=round_data['tournament_id'],
                    number=round_data['number'],
                    datetime=round_data['datetime'],
                    status=round_data['status']
                )
                db.session.add(new_round)
            
            # Migrate RoundPairings
            logger.info("Migrating Round Pairings...")
            cursor.execute("SELECT * FROM round_pairing")
            pairings = cursor.fetchall()
            for pairing in pairings:
                new_pairing = RoundPairing(
                    id=pairing['id'],
                    round_id=pairing['round_id'],
                    white_player_id=pairing['white_player_id'],
                    black_player_id=pairing['black_player_id'],
                    result=pairing['result']
                )
                db.session.add(new_pairing)
            
            # Migrate TournamentPlayers
            logger.info("Migrating Tournament Players...")
            cursor.execute("SELECT * FROM tournament_player")
            tournament_players = cursor.fetchall()
            for tp in tournament_players:
                new_tp = TournamentPlayer(
                    id=tp['id'],
                    tournament_id=tp['tournament_id'],
                    player_id=tp['player_id'],
                    initial_rating=tp['initial_rating'],
                    final_rating=tp['final_rating'],
                    current_score=tp['current_score']
                )
                db.session.add(new_tp)
            
            # Migrate Matches
            logger.info("Migrating Matches...")
            cursor.execute("SELECT * FROM match")
            matches = cursor.fetchall()
            for match in matches:
                new_match = Match(
                    id=match['id'],
                    tournament_id=match['tournament_id'],
                    round_number=match['round_number'],
                    round_start_time=match['round_start_time'],
                    black_player_id=match['black_player_id'],
                    white_player_id=match['white_player_id'],
                    result=match['result'],
                    date=match['date']
                )
                db.session.add(new_match)
            
            # Commit all changes to SQLite
            logger.info("Committing changes to SQLite...")
            db.session.commit()
            logger.info("Migration completed successfully!")
            
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        return False
    finally:
        cursor.close()
        conn.close()
    
    return True

if __name__ == "__main__":
    migrate_data()
