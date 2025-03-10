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
import logging

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
                info=form.info.data,
                status='upcoming',
                pairing_system=form.pairing_system.data
            )

            if form.cover_photo.data and form.cover_photo.data.filename:
                tournament.cover_photo = save_photo(form.cover_photo.data, 'tournaments')

            db.session.add(tournament)
            db.session.commit()

            # Add selected players to the tournament
            for player_id in (form.players.data or []):
                player = Player.query.get(player_id)
                if player:  # Only add if player exists
                    tournament_player = TournamentPlayer(
                        tournament=tournament,
                        player=player,
                        initial_rating=player.rating
                    )
                    db.session.add(tournament_player)

            db.session.commit()
            flash('Tournament created successfully!')
            return redirect(url_for('main.tournament_details', tournament_id=tournament.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating tournament: {str(e)}', 'error')
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
        new_players = set(form.players.data or [])

        # Remove players that are no longer selected
        for tp in tournament.players[:]:
            if tp.player_id not in new_players:
                db.session.delete(tp)

        # Add new players
        for player_id in new_players:
            if player_id not in current_players:
                player = Player.query.get(player_id)
                if player:  # Only add if player exists
                    tournament_player = TournamentPlayer(
                        tournament=tournament,
                        player=player,
                        initial_rating=player.rating
                    )
                    db.session.add(tournament_player)

        try:
            db.session.commit()
            flash('Tournament updated successfully!')
            return redirect(url_for('main.tournament_details', tournament_id=tournament.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating tournament: {str(e)}', 'error')
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

    # When showing the form initially (GET request)
    if request.method == 'GET':
        # No need to set form fields as they're already populated with obj=player
        pass

    if form.validate_on_submit():
        try:
            player.first_name = form.first_name.data
            player.middle_name = form.middle_name.data
            player.last_name = form.last_name.data
            player.state = form.state.data
            if current_user.is_admin:
                player.email = form.email.data
                player.phone = form.phone.data

            # Only update photos if new ones are uploaded
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

        # Check if we have enough players
        if len(tournament_players) < 2:
            flash('At least 2 players are required to create pairings.', 'error')
            db.session.delete(new_round)
            db.session.commit()
            return redirect(url_for('main.tournament_details', tournament_id=tournament_id))

        # Generate pairings based on tournament system
        if tournament.pairing_system == 'round_robin':
            pairs = round_robin_pairing(tournament_players)
        elif tournament.pairing_system == 'macmahon':
            pairs = macmahon_pairing(tournament_players)
        else:  # default to Swiss
            pairs = swiss_pairing(tournament_players)

        # Create pairings
        for white, black in pairs:
            if black is not None:  # Skip byes
                pairing = RoundPairing(
                    round=new_round,
                    white_player=white,
                    black_player=black
                )
                db.session.add(pairing)

        db.session.commit()
        flash(f'Round {round_number} created successfully!')

    except Exception as e:
        db.session.rollback()
        flash(f'Error creating round: {str(e)}', 'error')
        print(f"Error creating round: {str(e)}")  # Debug log

    return redirect(url_for('main.tournament_details', tournament_id=tournament_id))

@main_bp.route('/tournament/<int:tournament_id>/manual_pairing', methods=['POST'])
@login_required
def manual_pairing(tournament_id):
    if not current_user.is_admin:
        flash('Access denied.')
        return redirect(url_for('main.tournament_details', tournament_id=tournament_id))

    tournament = Tournament.query.get_or_404(tournament_id)

    try:
        # Get the list of white and black players
        white_players = request.form.getlist('white_players[]')
        black_players = request.form.getlist('black_players[]')

        # Validate that we have equal numbers of white and black players
        if len(white_players) != len(black_players):
            flash('Unequal number of white and black players.')
            return redirect(url_for('main.tournament_details', tournament_id=tournament_id))

        if not white_players or not black_players:
            flash('Please select at least one pair of players.')
            return redirect(url_for('main.tournament_details', tournament_id=tournament_id))

        # Create a new round
        round_number = len(tournament.rounds) + 1
        new_round = Round(
            tournament=tournament,
            number=round_number,
            datetime=datetime.utcnow(),
            status='pending'
        )
        db.session.add(new_round)

        # Create pairings
        for white_id, black_id in zip(white_players, black_players):
            if not white_id or not black_id:
                continue

            white_player = Player.query.get(white_id)
            black_player = Player.query.get(black_id)

            if white_player and black_player:
                pairing = RoundPairing(
                    round=new_round,
                    white_player=white_player,
                    black_player=black_player
                )
                db.session.add(pairing)

        # Update tournament status if needed
        if tournament.status == 'upcoming':
            tournament.status = 'ongoing'

        db.session.commit()
        flash('Manual pairings created successfully.')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating pairings: {str(e)}')
        logging.error(f"Error in manual_pairing: {str(e)}")

    return redirect(url_for('main.tournament_details', tournament_id=tournament_id))

@main_bp.route('/tournament/round/<int:round_id>/repair', methods=['POST'])
@login_required
def repair_round(round_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'})

    round = Round.query.get_or_404(round_id)

    try:
        # Clear existing pairings
        RoundPairing.query.filter_by(round_id=round_id).delete()

        # Get players and their current ratings
        tournament_players = [tp.player for tp in round.tournament.players]

        # Generate new pairings based on tournament system
        if round.tournament.pairing_system == 'round_robin':
            pairs = round_robin_pairing(tournament_players)
        elif round.tournament.pairing_system == 'macmahon':
            pairs = macmahon_pairing(tournament_players)
        else:  # default to Swiss
            pairs = swiss_pairing(tournament_players)

        # Create new pairings
        for white, black in pairs:
            if black is not None:  # Skip byes
                pairing = RoundPairing(
                    round=round,
                    white_player=white,
                    black_player=black
                )
                db.session.add(pairing)

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/tournament/pairing/<int:pairing_id>/result', methods=['POST'])
@login_required
def update_pairing_result(pairing_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'})

    pairing = RoundPairing.query.get_or_404(pairing_id)
    result = request.form.get('result')

    # Validate result format
    valid_results = ['B+R', 'W+R', 'B+T', 'W+T', 'Jigo']
    if result not in valid_results:
        flash('Invalid result format')
        return redirect(url_for('main.tournament_details', tournament_id=pairing.round.tournament_id))

    # Update pairing result
    pairing.result = result

    # Create a match record
    match = Match(
        tournament_id=pairing.round.tournament_id,
        round_number=pairing.round.number,
        round_start_time=pairing.round.datetime,
        black_player_id=pairing.black_player_id,
        white_player_id=pairing.white_player_id,
        result=result,
        date=datetime.utcnow()
    )

    try:
        db.session.add(match)
        db.session.commit()
        flash('Match result updated successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating match result: {str(e)}')

    return redirect(url_for('main.tournament_details', tournament_id=pairing.round.tournament_id))

@main_bp.route('/tournament/round/<int:round_id>/complete', methods=['POST'])
@login_required
def complete_round(round_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'})

    round = Round.query.get_or_404(round_id)

    # Update player ratings based on results
    glicko2 = Glicko2()

    for pairing in round.pairings:
        if pairing.result:
            # Calculate score (1 for win, 0.5 for draw, 0 for loss)
            if pairing.result == 'Jigo':
                white_score = black_score = 0.5
            elif pairing.result.startswith('W+'):
                white_score, black_score = 1.0, 0.0
            else:  # B+
                white_score, black_score = 0.0, 1.0

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

    # Mark round as completed
    round.status = 'completed'

    # Check if this was the last round
    tournament = round.tournament
    if all(r.status == 'completed' for r in tournament.rounds):
        tournament.status = 'completed'

        # Update final ratings for all tournament players
        for tp in tournament.players:
            tp.final_rating = tp.player.rating

    db.session.commit()
    return jsonify({'success': True})

def swiss_pairing(players):
    """
    Implementation of Swiss pairing system
    """
    # Sort players by rating
    sorted_players = sorted(players, key=lambda x: x.rating, reverse=True)
    pairs = []

    # Simple pairing: match players with closest ratings
    for i in range(0, len(sorted_players), 2):
        if i + 1 < len(sorted_players):
            # Randomly assign colors
            if random.random() > 0.5:
                pairs.append((sorted_players[i], sorted_players[i+1]))
            else:
                pairs.append((sorted_players[i+1], sorted_players[i]))

    # If odd number of players, last player gets a bye
    if len(sorted_players) % 2 == 1:
        pairs.append((sorted_players[-1], None))

    return pairs

def macmahon_pairing(players):
    """
    Implementation of MacMahon pairing system
    """
    # Group players by score/rating
    player_groups = {}
    for player in players:
        score = player.current_score
        if score not in player_groups:
            player_groups[score] = []
        player_groups[score].append(player)

    pairs = []
    unpaired = []

    # Pair within same score groups first
    for score in sorted(player_groups.keys(), reverse=True):
        group = player_groups[score]
        group_pairs = swiss_pairing(group)
        pairs.extend([p for p in group_pairs if p[1] is not None])
        if any(p[1] is None for p in group_pairs):
            unpaired.extend([p[0] for p in group_pairs if p[1] is None])

    # Pair remaining players across groups
    if unpaired:
        cross_pairs = swiss_pairing(unpaired)
        pairs.extend(cross_pairs)

    return pairs

def round_robin_pairing(players):
    """
    Implementation of Round Robin pairing system.
    Creates a schedule where each player plays against every other player once.
    """
    if len(players) % 2 != 0:
        # Add a "bye" player for odd number of players
        players = players + [None]

    n = len(players)
    pairings = []
    for round in range(n - 1):
        # Generate pairings for this round
        round_pairings = []
        for i in range(n // 2):
            player1 = players[i]
            player2 = players[n - 1 - i]
            if player1 and player2:  # Only create pairing if neither player is the "bye"
                # Alternate colors based on position
                if i % 2 == 0:
                    round_pairings.append((player1, player2))
                else:
                    round_pairings.append((player2, player1))

        # Rotate players for next round (keep first player fixed)
        players = [players[0]] + [players[-1]] + players[1:-1]
        pairings.extend(round_pairings)

    return pairings