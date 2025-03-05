from datetime import datetime, timedelta
from flask import Blueprint, render_template
from flask_login import login_required
from app import db
from models import Player, Tournament, Match

main_bp = Blueprint('main', __name__)

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

@main_bp.route('/tournament/<int:tournament_id>')
def tournament_details(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    return render_template('tournament_details.html', tournament=tournament)

@main_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
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