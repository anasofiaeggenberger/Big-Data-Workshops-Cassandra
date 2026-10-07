#!/usr/bin/env python3
"""Lee los CSV del mini-reto, materializa los JOIN y carga Cassandra.

La carga genera INSERT idempotentes agrupados en batches no logueados y los
envía a cqlsh dentro de cassandra3. Repetir el script deja las mismas filas:
la llave primaria hace que cada INSERT sea un upsert, no una fila adicional.
"""

import csv
import subprocess
import sys
from pathlib import Path


BATCH_SIZE = 100
RETRIES = 3


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
DATA = REPO / "data" / "mini-reto" / "G1-spotify"
KEYSPACE = "spotify_20240449"


def read_csv(name):
    with (DATA / name).open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def cql(value):
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def insert(table, columns, values):
    cols = ", ".join(columns)
    vals = ", ".join(cql(value) for value in values)
    return f"INSERT INTO {KEYSPACE}.{table} ({cols}) VALUES ({vals});"


def batches(table_rows):
    statements = []
    for table, rows in table_rows:
        statements.extend(rows)

    output = []
    for start in range(0, len(statements), BATCH_SIZE):
        output.append("BEGIN UNLOGGED BATCH")
        output.extend(f"  {statement}" for statement in statements[start:start + BATCH_SIZE])
        output.append("APPLY BATCH;")
    return "\n".join(output)


def build_load():
    usuarios = read_csv("usuarios.csv")
    canciones = {row["cancion_id"]: row for row in read_csv("canciones.csv")}
    playlist_canciones = read_csv("playlist_canciones.csv")
    reproducciones = read_csv("reproducciones.csv")

    perfil = [
        insert(
            "perfil_por_usuario",
            ("usuario_id", "nombre", "pais", "plan"),
            (row["usuario_id"], row["nombre"], row["pais"], row["plan"]),
        )
        for row in usuarios
    ]

    recientes = []
    por_dia = []
    for row in reproducciones:
        song = canciones[row["cancion_id"]]
        recientes.append(
            insert(
                "reproducciones_por_usuario",
                (
                    "usuario_id",
                    "reproducida_en",
                    "reproduccion_id",
                    "titulo",
                    "artista",
                    "cancion_id",
                    "segundos_escuchados",
                ),
                (
                    row["usuario_id"],
                    row["reproducida_en"],
                    int(row["reproduccion_id"]),
                    song["titulo"],
                    song["artista"],
                    row["cancion_id"],
                    int(row["segundos_escuchados"]),
                ),
            )
        )
        por_dia.append(
            insert(
                "reproducciones_por_cancion_dia",
                (
                    "cancion_id",
                    "dia",
                    "reproduccion_id",
                    "usuario_id",
                    "reproducida_en",
                    "segundos_escuchados",
                ),
                (
                    row["cancion_id"],
                    row["reproducida_en"][:10],
                    int(row["reproduccion_id"]),
                    row["usuario_id"],
                    row["reproducida_en"],
                    int(row["segundos_escuchados"]),
                ),
            )
        )

    playlistas = []
    for row in playlist_canciones:
        song = canciones[row["cancion_id"]]
        playlistas.append(
            insert(
                "canciones_por_playlist",
                ("playlist_id", "posicion", "cancion_id", "titulo", "artista"),
                (
                    row["playlist_id"],
                    int(row["posicion"]),
                    row["cancion_id"],
                    song["titulo"],
                    song["artista"],
                ),
            )
        )

    counts = {
        "perfil_por_usuario": len(perfil),
        "reproducciones_por_usuario": len(recientes),
        "canciones_por_playlist": len(playlistas),
        "reproducciones_por_cancion_dia": len(por_dia),
    }
    rows = [
        ("perfil_por_usuario", perfil),
        ("reproducciones_por_usuario", recientes),
        ("canciones_por_playlist", playlistas),
        ("reproducciones_por_cancion_dia", por_dia),
    ]
    return counts, batches(rows)


def run_cql(script):
    for attempt in range(1, RETRIES + 1):
        try:
            result = subprocess.run(
                ["docker", "exec", "-i", "cassandra3", "cqlsh"],
                input=script,
                text=True,
                capture_output=True,
                timeout=900,
                check=False,
            )
        except subprocess.TimeoutExpired:
            print(f"Intento {attempt}/{RETRIES}: timeout; reintento la carga idempotente.", file=sys.stderr)
            continue
        if result.returncode == 0:
            return
        print(f"Intento {attempt}/{RETRIES}: cqlsh terminó con código {result.returncode}.", file=sys.stderr)
        if result.stderr:
            print(result.stderr[-4000:], file=sys.stderr)
    raise SystemExit("No se pudo completar la carga después de los reintentos.")


def main():
    counts, load = build_load()
    schema = (HERE / "modelo.cql").read_text(encoding="utf-8")
    script = schema + "\nCONSISTENCY QUORUM;\n" + load + "\n"
    run_cql(script)
    for table, count in counts.items():
        print(f"{table}: {count} filas enviadas")


if __name__ == "__main__":
    main()
