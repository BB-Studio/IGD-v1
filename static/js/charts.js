// Charts initialization and configuration

function createPlayerRatingChart(containerId, ratingHistory) {
    const ctx = document.getElementById(containerId);
    if (!ctx) return;

    const dates = ratingHistory.map(entry => entry.date);
    const ratings = ratingHistory.map(entry => entry.rating);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'Rating History',
                data: ratings,
                borderColor: 'rgb(13, 202, 240)',
                backgroundColor: 'rgba(13, 202, 240, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Rating Progress'
                }
            },
            scales: {
                y: {
                    min: Math.min(...ratings) - 100,
                    max: Math.max(...ratings) + 100
                }
            }
        }
    });
}

function createTournamentStatsChart(containerId, playerData) {
    const ctx = document.getElementById(containerId);
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: playerData.map(p => p.name),
            datasets: [{
                label: 'Rating Change',
                data: playerData.map(p => p.ratingChange),
                backgroundColor: playerData.map(p => 
                    p.ratingChange >= 0 ? 'rgba(40, 167, 69, 0.7)' : 'rgba(220, 53, 69, 0.7)'
                )
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Rating Changes'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function createWinRateChart(containerId, winData) {
    const ctx = document.getElementById(containerId);
    if (!ctx) return;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Wins', 'Losses', 'Draws'],
            datasets: [{
                data: [winData.wins, winData.losses, winData.draws],
                backgroundColor: [
                    'rgba(40, 167, 69, 0.7)',  // Green for wins
                    'rgba(220, 53, 69, 0.7)',  // Red for losses
                    'rgba(108, 117, 125, 0.7)' // Gray for draws
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                title: {
                    display: true,
                    text: 'Win/Loss Distribution'
                }
            }
        }
    });
}