from math import sqrt, pi, log, exp

class Glicko2:
    def __init__(self, tau=0.5):
        self.tau = tau
        self._volatility_algorithm = self._volatility_illinois

    def _g(self, rd):
        return 1 / sqrt(1 + (3 * rd**2) / (pi**2))

    def _E(self, r, r_j, g_j):
        return 1 / (1 + exp(-g_j * (r - r_j)))

    def _volatility_illinois(self, v, delta, phi, sigma, tau):
        a = log(sigma**2)
        def f(x):
            ex = exp(x)
            num = ex * (delta**2 - phi**2 - v - ex)
            den = 2 * ((phi**2 + v + ex)**2)
            return x - a - (tau**2) * num / den
        
        # Illinois algorithm
        eps = 0.000001
        A = a
        B = float('inf')
        if delta**2 > phi**2 + v:
            B = log(delta**2 - phi**2 - v)
        else:
            k = 1
            while f(a - k * tau) < 0:
                k += 1
            B = a - k * tau
        
        fA = f(A)
        fB = f(B)
        while abs(B - A) > eps:
            C = A + (A - B) * fA / (fB - fA)
            fC = f(C)
            if fC * fB < 0:
                A = B
                fA = fB
            else:
                fA = fA / 2
            B = C
            fB = fC
        
        return exp(A / 2)

    def rate(self, rating, rd, vol, outcomes):
        # Convert ratings to Glicko-2 scale
        r = (rating - 1500) / 173.7178
        phi = rd / 173.7178

        v = 0
        delta = 0
        
        for opponent_rating, opponent_rd, score in outcomes:
            # Convert opponent ratings to Glicko-2 scale
            r_j = (opponent_rating - 1500) / 173.7178
            phi_j = opponent_rd / 173.7178
            
            g_j = self._g(phi_j)
            E_j = self._E(r, r_j, g_j)
            
            v += (g_j**2) * E_j * (1 - E_j)
            delta += g_j * (score - E_j)
        
        if v > 0:
            delta /= v
            
            # Update volatility
            sigma_prime = self._volatility_algorithm(v, delta, phi, vol, self.tau)
            
            # Update rating deviation
            phi_star = sqrt(phi**2 + sigma_prime**2)
            phi_prime = 1 / sqrt(1/phi_star**2 + 1/v)
            
            # Update rating
            r_prime = r + phi_prime**2 * delta
            
            # Convert back to original scale
            return (r_prime * 173.7178 + 1500,
                   phi_prime * 173.7178,
                   sigma_prime)
        
        return rating, rd, vol
