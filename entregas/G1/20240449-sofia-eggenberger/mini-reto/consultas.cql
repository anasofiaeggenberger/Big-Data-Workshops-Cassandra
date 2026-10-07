USE spotify_20240449;

-- C1. Perfil de un usuario.
SELECT usuario_id, nombre, pais, plan
FROM perfil_por_usuario
WHERE usuario_id = 'u116';

-- C2. Las 10 canciones que el usuario escuchó más recientemente.
SELECT reproducida_en, titulo, artista
FROM reproducciones_por_usuario
WHERE usuario_id = 'u031'
LIMIT 10;

-- C3. Las canciones de una playlist, en su orden.
SELECT posicion, titulo, artista
FROM canciones_por_playlist
WHERE playlist_id = 'p15';

-- C4. Cuántas veces se reprodujo una canción en un día.
SELECT count(*) AS reproducciones
FROM reproducciones_por_cancion_dia
WHERE cancion_id = 'c017' AND dia = '2026-09-09';
