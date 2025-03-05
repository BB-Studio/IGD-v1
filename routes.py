from datetime import datetime, timedelta
import os
import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import markdown2
from app import db
from models import Player, Tournament, Match, TournamentPlayer, Round, RoundPairing
from forms import PlayerForm, TournamentForm  
from glicko import Glicko2

main_bp = Blueprint('main', __name__)

def save_photo(photo, folder):
    if not photo or not photo.filename:
        return None
    filename = secure_filename(photo.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{timestamp}_{filename}"

    # Create upload directory if it doesn't exist
    upload_path = os.path.join(current_app.root_path, 'static', 'uploads', folder)
    os.makedirs(upload_path, exist_ok=True)

    photo.save(os.path.join(upload_path, unique_filename))
    return f'uploads/{folder}/{unique_filename}'

@main_bp.route('/')
def index():
    top_players = Player.query.order_by(Player.rating.desc()).limit(10).all()
    ongoing_tournaments = Tournament.query.filter_by(status='ongoing').all()
    upcoming_tournaments = Tournament.query.filter_by(status='upcoming').all()
    return render_template('home.html', 
                         top_players=top_players,
                         ongoing_tournaments=ongoing_tournaments,
                         upcoming_tournaments=upcoming_tournaments)

@main_bp.route('/players')
def players():
    players = Player.query.order_by(Player.rating.desc()).all()
    return render_template('players.html', players=players)

@main_bp.route('/add_player', methods=['GET', 'POST'])
@login_required
def add_player():
    form = PlayerForm()
    if form.validate_on_submit():
        player = Player(
            first_name=form.first_name.data,
            middle_name=form.middle_name.data,
            last_name=form.last_name.data,
            state=form.state.data,
            email=form.email.data if current_user.is_admin else None,
            phone=form.phone.data if current_user.is_admin else None
        )

        if form.player_photo.data and form.player_photo.data.filename:
            player.player_photo = save_photo(form.player_photo.data, 'players')

        if current_user.is_admin and form.id_card_photo.data and form.id_card_photo.data.filename:
            player.id_card_photo = save_photo(form.id_card_photo.data, 'id_cards')

        db.session.add(player)
        db.session.commit()
        flash('Player added successfully!')
        return redirect(url_for('main.players'))

    return render_template('add_player.html', form=form)

@main_bp.route('/player/<int:player_id>')
def player_stats(player_id):
    player = Player.query.get_or_404(player_id)
    recent_matches = Match.query.filter(
        (Match.black_player_id == player_id) | (Match.white_player_id == player_id)
    ).order_by(Match.date.desc()).limit(10).all()

    # Calculate win stats
    wins = 0
    losses = 0
    draws = 0
    for match in recent_matches:
        if match.black_player_id == player_id:
            if match.result.startswith('B+'): wins += 1
            elif match.result.startswith('W+'): losses += 1
            else: draws += 1
        else:  # player is white
            if match.result.startswith('W+'): wins += 1
            elif match.result.startswith('B+'): losses += 1
            else: draws += 1

    win_stats = {
        'wins': wins,
        'losses': losses,
        'draws': draws
    }

    # Get rating history from tournament participations
    tournament_players = TournamentPlayer.query.filter_by(player_id=player_id).all()
    rating_history = []

    # Add initial rating point
    first_tournament = min(tournament_players, key=lambda tp: tp.tournament.start_date) if tournament_players else None
    if first_tournament:
        rating_history.append({
            'date': first_tournament.tournament.start_date.strftime('%Y-%m-%d'),
            'rating': first_tournament.initial_rating
        })

    # Add rating changes from tournaments
    for tp in tournament_players:
        if tp.final_rating:  # Only include completed tournaments
            rating_history.append({
                'date': tp.tournament.end_date.strftime('%Y-%m-%d'),
                'rating': tp.final_rating
            })

    # Add current rating if different from last tournament rating
    if not rating_history or rating_history[-1]['rating'] != player.rating:
        rating_history.append({
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'rating': player.rating
        })

    # Sort rating history by date
    rating_history.sort(key=lambda x: x['date'])

    print("Debug - win_stats:", win_stats)  # Debug print
    print("Debug - rating_history:", rating_history)  # Debug print

    return render_template('player_stats.html', 
                         player=player, 
                         recent_matches=recent_matches,
                         win_stats=win_stats,
                         rating_history=rating_history)

@main_bp.route('/tournaments')
def tournaments():
    ongoing = Tournament.query.filter_by(status='ongoing').all()
    upcoming = Tournament.query.filter_by(status='upcoming').all()
    completed = Tournament.query.filter_by(status='completed').order_by(Tournament.end_date.desc()).limit(5).all()
    return render_template('tournaments.html', 
                         ongoing_tournaments=ongoing,
                         upcoming_tournaments=upcoming,
                         completed_tournaments=completed)

@main_bp.route('/add_tournament', methods=['GET', 'POST'])
@login_required
def add_tournament():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))

    form = TournamentForm()
    form.players.choices = [(p.id, f"{p.name} (ID: {p.player_id})") for p in Player.query.order_by(Player.rating.desc()).all()]

    if form.validate_on_submit():
        try:
            # Create upload directories if they don't exist
            uploads_path = os.path.join(current_app.root_path, 'static', 'uploads')
            tournaments_path = os.path.join(uploads_path, 'tournaments')
            os.makedirs(tournaments_path, exist_ok=True)

            tournament = Tournament(
                name=form.name.data,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                state=form.state.data,
                info=form.info.data if form.info.data else "",
                status='upcoming',
                pairing_system=form.pairing_system.data
            )

            if form.cover_photo.data and hasattr(form.cover_photo.data, 'filename') and form.cover_photo.data.filename:
                tournament.cover_photo = save_photo(form.cover_photo.data, 'tournaments')

            db.session.add(tournament)
            db.session.commit()

            # Add selected players to the tournament
            for player_id in form.players.data:
                player = Player.query.get(player_id)
                if player:
                    tournament_player = TournamentPlayer(
                        tournament=tournament,
                        player=player,
                        initial_rating=player.rating,
                        current_score=0.0
                    )
                    db.session.add(tournament_player)

            db.session.commit()
            flash('Tournament created successfully!')
            return redirect(url_for('main.tournament_details', tournament_id=tournament.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating tournament: {str(e)}', 'error')
            print(f"Error creating tournament: {str(e)}")  # Debug log
    elif form.errors:
        # Flash form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {field}: {error}", 'error')

    return render_template('add_tournament.html', form=form)

@main_bp.route('/edit_tournament/<int:tournament_id>', methods=['GET', 'POST'])
@login_required
def edit_tournament(tournament_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))

    tournament = Tournament.query.get_or_404(tournament_id)
    if tournament.status == 'completed':
        flash('Completed tournaments cannot be edited.')
        return redirect(url_for('main.tournament_details', tournament_id=tournament.id))

    form = TournamentForm(obj=tournament)
    form.players.choices = [(p.id, f"{p.name} (ID: {p.player_id})") for p in Player.query.order_by(Player.rating.desc()).all()]

    # Set current players when displaying the form
    if request.method == 'GET':
        form.players.data = [tp.player_id for tp in tournament.players]

    if form.validate_on_submit():
        try:
            tournament.name = form.name.data
            tournament.start_date = form.start_date.data
            tournament.end_date = form.end_date.data
            tournament.state = form.state.data
            tournament.info = form.info.data
            tournament.pairing_system = form.pairing_system.data

            # Only update cover photo if a new one is uploaded
            if form.cover_photo.data and hasattr(form.cover_photo.data, 'filename') and form.cover_photo.data.filename:
                old_photo = tournament.cover_photo
                tournament.cover_photo = save_photo(form.cover_photo.data, 'tournaments')
                # Delete old photo if it exists
                if old_photo:
                    try:
                        os.remove(os.path.join(current_app.root_path, 'static', old_photo))
                    except OSError:
                        pass  # Ignore file deletion errors

            # Update players
            current_players = set(tp.player_id for tp in tournament.players)
            new_players = set(form.players.data)

            # Remove players that are no longer selected
            for tp in list(tournament.players):
                if tp.player_id not in new_players:
                    db.session.delete(tp)

            # Add new players
            for player_id in new_players:
                if player_id not in current_players:
                    player = Player.query.get(player_id)
                    if player:
                        tournament_player = TournamentPlayer(
                            tournament=tournament,
                            player=player,
                            initial_rating=player.rating
                        )
                        db.session.add(tournament_player)

            db.session.commit()
            flash('Tournament updated successfully!')
            return redirect(url_for('main.tournament_details', tournament_id=tournament.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating tournament: {str(e)}', 'error')
            print(f"Error updating tournament: {str(e)}")  # Debug log
    elif form.errors:
        # Flash form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {field}: {error}", 'error')

    return render_template('add_tournament.html', form=form, tournament=tournament)

@main_bp.route('/delete_tournament/<int:tournament_id>', methods=['POST'])
@login_required
def delete_tournament(tournament_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))

    tournament = Tournament.query.get_or_404(tournament_id)
    if tournament.status == 'completed':
        flash('Completed tournaments cannot be deleted.')
        return redirect(url_for('main.tournaments'))

    # Delete associated records
    TournamentPlayer.query.filter_by(tournament_id=tournament.id).delete()
    Match.query.filter_by(tournament_id=tournament.id).delete()

    # Delete cover photo if exists
    if tournament.cover_photo:
        try:
            os.remove(os.path.join(current_app.root_path, 'static', tournament.cover_photo))
        except OSError:
            pass  # Ignore file deletion errors

    db.session.delete(tournament)
    db.session.commit()
    flash('Tournament deleted successfully!')
    return redirect(url_for('main.tournaments'))

@main_bp.route('/delete_player/<int:player_id>', methods=['POST'])
@login_required
def delete_player(player_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))

    player = Player.query.get_or_404(player_id)

    # Check if player is in any ongoing tournaments
    ongoing_tournaments = TournamentPlayer.query.join(Tournament).filter(
        TournamentPlayer.player_id == player.id,
        Tournament.status != 'completed'
    ).first()

    if ongoing_tournaments:
        flash('Cannot delete player who is participating in ongoing tournaments.')
        return redirect(url_for('main.players'))

    # Delete photos if they exist
    if player.player_photo:
        try:
            os.remove(os.path.join(current_app.root_path, 'static', player.player_photo))
        except OSError:
            pass
    if player.id_card_photo:
        try:
            os.remove(os.path.join(current_app.root_path, 'static', player.id_card_photo))
        except OSError:
            pass

    # Delete associated records
    TournamentPlayer.query.filter_by(player_id=player.id).delete()
    Match.query.filter(
        (Match.black_player_id == player.id) | (Match.white_player_id == player.id)
    ).delete()

    db.session.delete(player)
    db.session.commit()
    flash('Player deleted successfully!')
    return redirect(url_for('main.players'))

@main_bp.route('/tournament/<int:tournament_id>')
def tournament_details(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    markdown_html = markdown2.markdown(tournament.info) if tournament.info else ''

    return render_template('tournament_details.html', 
                         tournament=tournament, 
                         tournament_info_html=markdown_html)

@main_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))

    player_stats = {
        'total': Player.query.count(),
        'active': Player.query.filter(Player.last_active >= (datetime.utcnow() - timedelta(days=90))).count(),
        'avg_rating': db.session.query(db.func.avg(Player.rating)).scalar() or 0
    }

    tournament_stats = {
        'ongoing': Tournament.query.filter_by(status='ongoing').count(),
        'upcoming': Tournament.query.filter_by(status='upcoming').count(),
        'completed': Tournament.query.filter_by(status='completed').count()
    }

    # Add system statistics
    system_stats = {
        'db_size': 'N/A',  # This would require additional setup to track
        'last_backup': datetime.utcnow().strftime('%Y-%m-%d'),
        'version': '1.0.0'
    }

    # Get recent activity
    recent_activity = []
    # Get last 5 tournaments
    recent_tournaments = Tournament.query.order_by(Tournament.start_date.desc()).limit(5).all()
    for tournament in recent_tournaments:
        recent_activity.append({
            'date': tournament.start_date,
            'event_type': 'Tournament Created',
            'details': f'Tournament: {tournament.name}'
        })

    # Get last 5 player registrations
    recent_players = Player.query.order_by(Player.last_active.desc()).limit(5).all()
    for player in recent_players:
        recent_activity.append({
            'date': player.last_active,
            'event_type': 'Player Registration',
            'details': f'Player: {player.name}'
        })

    # Sort combined activity by date
    recent_activity.sort(key=lambda x: x['date'], reverse=True)
    recent_activity = recent_activity[:5]  # Keep only the 5 most recent activities

    return render_template('admin/dashboard.html', 
                         player_stats=player_stats,
                         tournament_stats=tournament_stats,
                         system_stats=system_stats,
                         recent_activity=recent_activity)

@main_bp.route('/tournament/<int:tournament_id>/complete', methods=['POST'])
@login_required
def complete_tournament(tournament_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))

    tournament = Tournament.query.get_or_404(tournament_id)
    if tournament.status != 'ongoing':
        flash('Only ongoing tournaments can be marked as completed.')
        return redirect(url_for('main.tournament_details', tournament_id=tournament.id))

    # Initialize Glicko2 calculator
    glicko2 = Glicko2()

    # Get all tournament players and their matches
    for tp in tournament.players:
        player = tp.player
        matches = []

        # Collect all matches for this player
        for match in tournament.matches:
            if match.black_player_id == player.id or match.white_player_id == player.id:
                opponent = match.white_player if match.black_player_id == player.id else match.black_player
                # Convert match result to score (1 for win, 0.5 for draw, 0 for loss)
                score = 0.5  # Default for draw
                if match.result.startswith('B+') and match.black_player_id == player.id:
                    score = 1.0
                elif match.result.startswith('W+') and match.white_player_id == player.id:
                    score = 1.0
                elif match.result.startswith('B+') and match.white_player_id == player.id:
                    score = 0.0
                elif match.result.startswith('W+') and match.black_player_id == player.id:
                    score = 0.0

                matches.append((opponent.rating, opponent.rating_deviation, score))

        if matches:  # Only update if player had matches
            # Calculate new rating
            new_rating, new_rd, new_vol = glicko2.rate(player.rating, 
                                                      player.rating_deviation,
                                                      player.volatility,
                                                      matches)

            # Update player's rating
            player.rating = new_rating
            player.rating_deviation = new_rd
            player.volatility = new_vol
            player.last_active = datetime.utcnow()

            # Store final rating in tournament_player
            tp.final_rating = new_rating

    # Mark tournament as completed
    tournament.status = 'completed'
    db.session.commit()

    flash('Tournament marked as completed and player ratings have been updated.')
    return redirect(url_for('main.tournament_details', tournament_id=tournament.id))

@main_bp.route('/edit_player/<int:player_id>', methods=['GET', 'POST'])
@login_required
def edit_player(player_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))

    player = Player.query.get_or_404(player_id)
    form = PlayerForm(obj=player)

    if form.validate_on_submit():
        try:
            player.first_name = form.first_name.data
            player.middle_name = form.middle_name.data
            player.last_name = form.last_name.data
            player.state = form.state.data
            if current_user.is_admin:
                player.email = form.email.data
                player.phone = form.phone.data

            # Only update photos if new ones are uploaded and they have filenames
            if form.player_photo.data and hasattr(form.player_photo.data, 'filename') and form.player_photo.data.filename:
                old_photo = player.player_photo
                player.player_photo = save_photo(form.player_photo.data, 'players')
                # Delete old photo if it exists
                if old_photo:
                    try:
                        os.remove(os.path.join(current_app.root_path, 'static', old_photo))
                    except OSError:
                        pass

            if current_user.is_admin and form.id_card_photo.data and hasattr(form.id_card_photo.data, 'filename') and form.id_card_photo.data.filename:
                old_photo = player.id_card_photo
                player.id_card_photo = save_photo(form.id_card_photo.data, 'id_cards')
                # Delete old photo if it exists
                if old_photo:
                    try:
                        os.remove(os.path.join(current_app.root_path, 'static', old_photo))
                    except OSError:
                        pass

            db.session.commit()
            flash('Player updated successfully!')
            return redirect(url_for('main.players'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating player: {str(e)}', 'error')
    elif form.errors:
        # Flash form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {field}: {error}", 'error')

    return render_template('add_player.html', form=form, player=player)

@main_bp.route('/tournament/<int:tournament_id>/round', methods=['POST'])
@login_required
def create_round(tournament_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.tournament_details', tournament_id=tournament_id))

    tournament = Tournament.query.get_or_404(tournament_id)

    # Validate tournament status
    if tournament.status == 'completed':
        flash('Cannot create rounds for completed tournaments.')
        return redirect(url_for('main.tournament_details', tournament_id=tournament_id))

    try:
        # Update tournament status to ongoing if it's not already
        if tournament.status == 'upcoming':
            tournament.status = 'ongoing'
            db.session.commit()

        # Create new round
        round_number = len(tournament.rounds) + 1

        # Make sure datetime is provided
        if 'datetime' not in request.form or not request.form['datetime']:
            flash('Round date and time are required', 'error')
            return redirect(url_for('main.tournament_details', tournament_id=tournament_id))

        try:
            round_datetime = datetime.strptime(request.form['datetime'], '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DDTHH:MM format.', 'error')
            return redirect(url_for('main.tournament_details', tournament_id=tournament_id))

        # Get pairing system from form or use tournament default
        pairing_system = request.form.get('pairing_system', tournament.pairing_system)
        
        new_round = Round(
            tournament=tournament,
            number=round_number,
            datetime=round_datetime,
            status='pending'
        )
        db.session.add(new_round)
        db.session.commit()

        # Get players and their current ratings
        tournament_players = [tp.player for tp in tournament.players]
        
        # Set current tournament ID for each player (used by MacMahon pairing)
        for player in tournament_players:
            player.current_tournament_id = tournament.id

        # Check if we have enough players
        if len(tournament_players) < 2:
            flash('At least 2 players are required to create pairings.', 'error')
            db.session.delete(new_round)
            db.session.commit()
            return redirect(url_for('main.tournament_details', tournament_id=tournament_id))

        # Get all existing pairings to avoid duplicate matches
        played_matches = set()
        for r in tournament.rounds:
            if r.id != new_round.id:  # Don't include the current round
                for pairing in r.pairings:
                    if pairing.black_player_id:  # Only add if not a bye
                        played_matches.add((pairing.white_player_id, pairing.black_player_id))
                        played_matches.add((pairing.black_player_id, pairing.white_player_id))

        # Generate pairings based on tournament system or form selection
        if pairing_system == 'auto' or pairing_system == 'macmahon':
            pairs = macmahon_pairing(tournament_players, played_matches)
        elif pairing_system == 'round_robin':
            pairs = round_robin_pairing(tournament_players, round_number, played_matches)
        else:  # default to Swiss
            pairs = swiss_pairing(tournament_players, played_matches)

        # Create pairings
        for white, black in pairs:
            if black is not None:  # Regular pairing
                pairing = RoundPairing(
                    round=new_round,
                    white_player=white,
                    black_player=black
                )
                db.session.add(pairing)
            else:  # Bye
                pairing = RoundPairing(
                    round=new_round,
                    white_player=white,
                    black_player=None,
                    result="Bye"
                )
                db.session.add(pairing)
                
                # Update player score for the bye
                tp = TournamentPlayer.query.filter_by(
                    tournament_id=tournament.id, 
                    player_id=white.id
                ).first()
                if tp:
                    tp.current_score += 1  # Add a win for the bye

        db.session.commit()
        flash(f'Round {round_number} created successfully!')

    except Exception as e:
        db.session.rollback()
        flash(f'Error creating round: {str(e)}', 'error')
        print(f"Error creating round: {str(e)}")  # Debug log

    return redirect(url_for('main.tournament_details', tournament_id=tournament_id))

@main_bp.route('/tournament/<int:round_id>/repair', methods=['POST'])
@login_required
def repair_round(round_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'})

    round = Round.query.get_or_404(round_id)

    # Clear existing pairings
    RoundPairing.query.filter_by(round_id=round_id).delete()

    # Get players and their current ratings
    tournament_players = [tp.player for tp in round.tournament.players]
    
    # Set current tournament ID for each player (used by MacMahon pairing)
    for player in tournament_players:
        player.current_tournament_id = round.tournament.id

    # Get all existing pairings to avoid duplicate matches (from other rounds)
    played_matches = set()
    for r in round.tournament.rounds:
        if r.id != round.id:  # Don't include the current round
            for pairing in r.pairings:
                played_matches.add((pairing.white_player_id, pairing.black_player_id))
                played_matches.add((pairing.black_player_id, pairing.white_player_id))

    # Generate new pairings
    if round.tournament.pairing_system == 'macmahon':
        pairs = macmahon_pairing(tournament_players, played_matches)
    elif round.tournament.pairing_system == 'round_robin':
        pairs = round_robin_pairing(tournament_players, round.number, played_matches)
    else:
        pairs = swiss_pairing(tournament_players, played_matches)

    # Create new pairings
    for white, black in pairs:
        if black is not None:
            pairing = RoundPairing(
                round=round,
                white_player=white,
                black_player=black
            )
            db.session.add(pairing)
        else:
            # Create a "bye" entry
            pairing = RoundPairing(
                round=round,
                white_player=white,
                black_player=None,
                result="Bye"
            )
            db.session.add(pairing)

    db.session.commit()
    return jsonify({'success': True})

@main_bp.route('/tournament/<int:round_id>/manual_pairing', methods=['GET', 'POST'])
@login_required
def manual_pairing(round_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))
        
    round = Round.query.get_or_404(round_id)
    tournament = round.tournament
    
    if request.method == 'POST':
        # Clear existing pairings
        RoundPairing.query.filter_by(round_id=round_id).delete()
        
        # Process form data to create new pairings
        player_pairs = []
        i = 0
        while f'white_player_{i}' in request.form:
            white_id = request.form.get(f'white_player_{i}')
            black_id = request.form.get(f'black_player_{i}')
            
            if white_id:
                if black_id and black_id != 'bye':
                    # Regular pairing
                    white_player = Player.query.get(white_id)
                    black_player = Player.query.get(black_id)
                    
                    pairing = RoundPairing(
                        round=round,
                        white_player=white_player,
                        black_player=black_player
                    )
                    db.session.add(pairing)
                elif white_id != 'bye':
                    # Bye
                    white_player = Player.query.get(white_id)
                    pairing = RoundPairing(
                        round=round,
                        white_player=white_player,
                        black_player=None,
                        result="Bye"
                    )
                    db.session.add(pairing)
            
            i += 1
            
        db.session.commit()
        flash('Manual pairings created successfully!')
        return redirect(url_for('main.tournament_details', tournament_id=tournament.id))
    
    # Get all players for this tournament
    players = [tp.player for tp in tournament.players]
    
    # Get existing pairings if any
    existing_pairings = RoundPairing.query.filter_by(round_id=round_id).all()
    
    # Mark players who are already paired
    paired_players = set()
    for pairing in existing_pairings:
        paired_players.add(pairing.white_player_id)
        if pairing.black_player_id:
            paired_players.add(pairing.black_player_id)
    
    # Get unpaired players
    unpaired_players = [p for p in players if p.id not in paired_players]
    
    return render_template('manual_pairing.html', 
                         round=round,
                         tournament=tournament,
                         players=players,
                         unpaired_players=unpaired_players,
                         existing_pairings=existing_pairings)

@main_bp.route('/tournament/pairing/<int:pairing_id>/result', methods=['POST'])
@login_required
def update_pairing_result(pairing_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.index'))

    pairing = RoundPairing.query.get_or_404(pairing_id)
    
    if pairing.result != "Bye":  # Don't change bye results
        pairing.result = request.form['result']
        db.session.commit()
        flash('Result updated successfully!')
    
    return redirect(url_for('main.tournament_details', tournament_id=pairing.round.tournament_id))

@main_bp.route('/tournament/round/<int:round_id>/complete', methods=['POST'])
@login_required
def complete_round(round_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'})

    round = Round.query.get_or_404(round_id)
    tournament = round.tournament

    # Check if all pairings have results
    incomplete_pairings = [p for p in round.pairings if not p.result]
    if incomplete_pairings and 'force' not in request.args:
        return jsonify({
            'success': False, 
            'error': 'Not all pairings have results. Please enter all results before completing the round.'
        })

    # Update player ratings and scores based on results
    glicko2 = Glicko2()

    for pairing in round.pairings:
        if pairing.result:
            # Skip byes
            if pairing.result == "Bye" or not pairing.black_player:
                continue
                
            # Calculate score (1 for win, 0.5 for draw, 0 for loss)
            if pairing.result == 'Jigo':
                white_score = black_score = 0.5
            elif pairing.result.startswith('W+'):
                white_score, black_score = 1.0, 0.0
            else:  # B+
                white_score, black_score = 0.0, 1.0

            # Update player tournament scores
            white_tp = TournamentPlayer.query.filter_by(
                tournament_id=tournament.id, 
                player_id=pairing.white_player_id
            ).first()
            
            black_tp = TournamentPlayer.query.filter_by(
                tournament_id=tournament.id, 
                player_id=pairing.black_player_id
            ).first()
            
            if white_tp:
                white_tp.current_score += white_score
            
            if black_tp:
                black_tp.current_score += black_score

            # Update white player rating
            white_matches = [(pairing.black_player.rating, 
                            pairing.black_player.rating_deviation, 
                            white_score)]
            new_white_rating, new_white_rd, new_white_vol = glicko2.rate(
                pairing.white_player.rating,
                pairing.white_player.rating_deviation,
                pairing.white_player.volatility,
                white_matches
            )

            # Update black player rating
            black_matches = [(pairing.white_player.rating, 
                            pairing.white_player.rating_deviation, 
                            black_score)]
            new_black_rating, new_black_rd, new_black_vol = glicko2.rate(
                pairing.black_player.rating,
                pairing.black_player.rating_deviation,
                pairing.black_player.volatility,
                black_matches
            )

            # Save new ratings
            pairing.white_player.rating = new_white_rating
            pairing.white_player.rating_deviation = new_white_rd
            pairing.white_player.volatility = new_white_vol
            pairing.white_player.last_active = datetime.utcnow()

            pairing.black_player.rating = new_black_rating
            pairing.black_player.rating_deviation = new_black_rd
            pairing.black_player.volatility = new_black_vol
            pairing.black_player.last_active = datetime.utcnow()
            
            # Create match record
            match = Match(
                tournament_id=tournament.id,
                round_number=round.number,
                round_start_time=round.datetime,
                black_player_id=pairing.black_player_id,
                white_player_id=pairing.white_player_id,
                result=pairing.result,
                date=datetime.utcnow()
            )
            db.session.add(match)

    # Mark round as completed
    round.status = 'completed'

    # Check if this was the last round
    if tournament.pairing_system == 'round_robin':
        total_rounds = (len(tournament.players) - 1) if len(tournament.players) % 2 == 0 else len(tournament.players)
        if len(tournament.rounds) >= total_rounds and all(r.status == 'completed' for r in tournament.rounds):
            tournament.status = 'completed'
    elif all(r.status == 'completed' for r in tournament.rounds):
        tournament.status = 'completed'

    db.session.commit()
    return jsonify({'success': True})

def swiss_pairing(players, played_matches=None):
    """
    Implementation of Swiss pairing system
    """
    if played_matches is None:
        played_matches = set()  # Set of tuples (player1_id, player2_id)
    
    # Sort players by rating
    sorted_players = sorted(players, key=lambda x: x.rating, reverse=True)
    pairs = []
    paired_players = set()

    # Try to pair players who haven't played against each other yet
    for i, player1 in enumerate(sorted_players):
        if player1.id in paired_players:
            continue
            
        for player2 in sorted_players[i+1:]:
            if player2.id in paired_players:
                continue
                
            pair_key1 = (player1.id, player2.id)
            pair_key2 = (player2.id, player1.id)
            
            # Check if these players have already played against each other
            if pair_key1 not in played_matches and pair_key2 not in played_matches:
                # Randomly assign colors
                if random.random() > 0.5:
                    pairs.append((player1, player2))
                else:
                    pairs.append((player2, player1))
                    
                paired_players.add(player1.id)
                paired_players.add(player2.id)
                break
        
        # If we couldn't find a pair, just pair with the next available player
        if player1.id not in paired_players:
            for player2 in sorted_players:
                if player2.id != player1.id and player2.id not in paired_players:
                    # Randomly assign colors
                    if random.random() > 0.5:
                        pairs.append((player1, player2))
                    else:
                        pairs.append((player2, player1))
                        
                    paired_players.add(player1.id)
                    paired_players.add(player2.id)
                    break

    # If odd number of players, last player gets a bye
    unpaired = [p for p in sorted_players if p.id not in paired_players]
    if unpaired:
        pairs.append((unpaired[0], None))

    return pairs

def macmahon_pairing(players, played_matches=None):
    """
    Implementation of MacMahon pairing system
    """
    if played_matches is None:
        played_matches = set()
        
    # Group players by score/rating
    player_groups = {}
    for player in players:
        # Get the player's TournamentPlayer record to get current_score
        tp = next((tp for tp in player.tournaments if tp.tournament_id == player.current_tournament_id), None)
        score = tp.current_score if tp else 0
        
        if score not in player_groups:
            player_groups[score] = []
        player_groups[score].append(player)

    pairs = []
    unpaired = []

    # Pair within same score groups first
    for score in sorted(player_groups.keys(), reverse=True):
        group = player_groups[score]
        group_pairs = swiss_pairing(group, played_matches)
        pairs.extend([p for p in group_pairs if p[1] is not None])
        if any(p[1] is None for p in group_pairs):
            unpaired.extend([p[0] for p in group_pairs if p[1] is None])

    # Pair remaining players across groups
    if unpaired:
        cross_pairs = swiss_pairing(unpaired, played_matches)
        pairs.extend(cross_pairs)

    return pairs

def round_robin_pairing(players, round_number, played_matches=None):
    """
    Implementation of Round Robin pairing system
    Based on a circle method: https://en.wikipedia.org/wiki/Round-robin_tournament#Scheduling_algorithm
    """
    if played_matches is None:
        played_matches = set()
        
    n = len(players)
    pairs = []
    
    # If odd number of players, add a "dummy" player for byes
    if n % 2 == 1:
        n += 1
        
    # Create a list of player indices
    indices = list(range(n))
    
    # For round i, player j plays against player (n-1-j+i) mod (n-1)
    # Player n-1 stays fixed
    fixed = indices[-1]
    rotating = indices[:-1]
    
    # Rotate (round_number - 1) times
    for _ in range((round_number - 1) % (n - 1)):
        rotating = [rotating[-1]] + rotating[:-1]
    
    # Create pairings
    for i in range(n // 2):
        if i == 0 and n % 2 == 1:  # Handle bye for the fixed player
            if len(players) <= fixed:  # The fixed position is the dummy
                pairs.append((players[rotating[0]], None))
            else:
                pairs.append((players[fixed], None))
        else:
            idx1 = rotating[i]
            idx2 = rotating[n - 2 - i]
            
            # Skip pairs that include the dummy player
            if len(players) <= idx1 or len(players) <= idx2:
                continue
                
            # Check if these players have already played
            pair_key1 = (players[idx1].id, players[idx2].id)
            pair_key2 = (players[idx2].id, players[idx1].id)
            
            if pair_key1 in played_matches or pair_key2 in played_matches:
                continue
                
            # Randomly assign colors or alternate based on round number
            if round_number % 2 == 0:
                pairs.append((players[idx1], players[idx2]))
            else:
                pairs.append((players[idx2], players[idx1]))
    
    return pairs