"""Motor estadístico de ApuestaEdge.

Módulos puros (sin I/O) que implementan los cálculos utilizados para
generar recomendaciones con valor esperado positivo:

- ``devig``    eliminación de la cuota (vig / margen de la casa)
- ``elo``      ratings Elo por deporte con ventaja de localía
- ``poisson``  modelo de goles Poisson basado en Elo (fútbol)
- ``kelly``    criterio de Kelly para dimensionar la apuesta
- ``ev``       valor esperado, edge y confianza bayesiana
- ``backtest`` ROI, drawdown, profit factor y significancia estadística
"""
