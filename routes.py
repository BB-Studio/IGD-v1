from datetime import datetime, timedelta
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import markdown2
from app import db
from models import Player, Tournament, Match, TournamentPlayer
from forms import PlayerForm, TournamentForm, MatchForm

main_bp = Blueprint('main', __name__)

def save_photo(photo, folder):
    if not photo:
        return None
    filename = secure_filename(photo.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{timestamp}_{filename}"
    photo.save(os.path.join(current_app.root_path, 'static', 'uploads', folder, unique_filename))
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

        if form.player_photo.data:
            player.player_photo = save_photo(form.player_photo.data, 'players')

        if current_user.is_admin and form.id_card_photo.data:
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
    return render_template('player_stats.html', player=player, recent_matches=recent_matches)

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
    form = TournamentForm()
    form.players.choices = [(p.id, p.name) for p in Player.query.order_by(Player.rating.desc()).all()]

    if form.validate_on_submit():
        tournament = Tournament(
            name=form.name.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            state=form.state.data,
            info=form.info.data,
            rounds=form.rounds.data
        )

        if form.cover_photo.data:
            tournament.cover_photo = save_photo(form.cover_photo.data, 'tournaments')

        db.session.add(tournament)
        db.session.commit()

        # Add selected players to the tournament
        for player_id in form.players.data:
            player = Player.query.get(player_id)
            tournament_player = TournamentPlayer(
                tournament=tournament,
                player=player,
                initial_rating=player.rating
            )
            db.session.add(tournament_player)

        db.session.commit()
        flash('Tournament created successfully!')
        return redirect(url_for('main.tournaments'))

    return render_template('add_tournament.html', form=form)

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

    return render_template('admin/dashboard.html', 
                         player_stats=player_stats,
                         tournament_stats=tournament_stats)

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
    # Assume Glicko2 class is defined elsewhere
    # from glicko2 import Glicko2
    glicko2 = Glicko2() # Placeholder - Replace with actual import if needed

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