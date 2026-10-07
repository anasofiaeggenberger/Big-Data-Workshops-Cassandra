# Checklist para manana

## Estado listo

- [x] Rama local: `entrega-20240449-ana-sofia-eggenberger`.
- [x] `origin` es el fork `https://github.com/anasofiaeggenberger/Big-Data-Workshops-Cassandra`.
- [x] `upstream` es `https://github.com/jcarriolaa/Big-Data-Workshops-Cassandra.git`.
- [x] Docker Desktop responde y reporta 7.7 GB para Docker, por encima de los 2 GB requeridos.
- [x] Imagen descargada: `cassandra:5.0.8`.
- [x] Parte 1 ejecutada con `ventas_G1.csv`: 75,000 filas cargadas.
- [x] La traza completa del Paso 4 está en `notas/traza-paso4.txt`.
- [x] En esa traza, la consulta por ciudad muestra `Executing single-partition query` en la línea 16 y `Read 11 live rows` en la línea 21: leyó 11 filas de una sola partición.
- [x] En esa traza, la consulta por producto muestra `Submitting range requests on 17 ranges` en la línea 43 y los `Executing seq scan` repetidos desde la línea 45: las lecturas suman 75,000 filas en 50 lecturas.
- [x] La consulta por producto devolvió 4,911 coincidencias, pero tuvo que leer las 75,000 filas.
- [!] `bash scripts/check.sh nodo` mostró una vez un fallo en la comprobación automática de `nodetool`, aunque la consulta directa inmediata mostró `cassandra1` en `UN` y el conteo fue 75,000; no se modificó el script y luego se ejecutó el `down -v` obligatorio.
- [x] La carpeta de entrega, `capturas/`, `mini-reto/`, `notas/` y `bitacora.md` ya existen. La bitácora sigue sin respuestas.
- [x] El `compose.yml` raíz y la copia de entrega tienen un solo servicio `cassandra3`, volumen `cassandra3-data`, puertos 9042 y 7000, y pasan `docker compose config`.
- [x] Mi IP Tailscale es `100.106.51.83`; está en `CASSANDRA_BROADCAST_ADDRESS`.
- [x] La IP Tailscale de Juan/cassandra1 es `100.71.193.83`; está en `CASSANDRA_SEEDS`.
- [x] La IP Tailscale de Víctor/cassandra2 es `100.88.43.68`.
- [x] Los puertos 7000 y 9042 estaban libres al revisar.
- [x] El firewall de aplicación de macOS está apagado (`State = 0`). Si se enciende, permitir entrada TCP a 7000 y 9042 para Docker/Cassandra.
- [x] El compose usa la red Docker `10.77.0.0/16`, separada de la red física.
- [!] Tailscale muestra mi equipo, pero Juan y Víctor todavía no aparecen como peers accesibles; validar esto antes de arrancar Cassandra.

## Lo que debo pedir al grupo

1. Confirmar que Juan/cassandra1 aparece en Tailscale como `100.71.193.83` y Víctor/cassandra2 como `100.88.43.68`, dentro del mismo tailnet.
2. Confirmar que desde cada laptop responden ping Tailscale y TCP 7000/9042 hacia las otras dos.
3. Confirmar que los tres usarán `UFM-G1`, `dc-g1`, `rack1`, Cassandra 5.0.8 y puertos publicados 7000/9042.
4. Acordar que Juan levanta `cassandra1` primero, el dueño de `cassandra2` lo levanta después de ver `cassandra1` en `UN`, y yo levanto `cassandra3` al final cuando ambos ya estén `UN`.
5. Confirmar que Juan, y solamente quien tiene `cassandra1`, crea el keyspace, crea la tabla y carga `ventas_G1.csv` una sola vez.
6. Coordinar las rondas de los Pasos 8 y 9: yo mantengo `cassandra3` encendido; el grupo detiene y vuelve a iniciar los nodos indicados abajo.
7. Revisar en cada laptop que el firewall permita tráfico entrante TCP 7000 y 9042 y que ninguna otra aplicación ocupe esos puertos. En esta Mac, si 7000 estuviera ocupado por `ControlCenter`, apagar Receptor de AirPlay en Ajustes del Sistema → General → AirDrop y Handoff.

## Orden exacto de la Parte 2

### Antes de todo

En mi laptop ejecutar:

```bash
docker compose down -v
```

Esto borra el nodo y los datos de la Parte 1. Es obligatorio porque, si se conserva el volumen, Cassandra puede rechazar el arranque con `Saved cluster name Test Cluster != configured name UFM-G1`.

Luego confirmar que el compose ya tenga las IP Tailscale de cada nodo en `CASSANDRA_BROADCAST_ADDRESS` y `CASSANDRA_SEEDS`, y validar:

```bash
docker compose config
```

### Arranque secuencial

1. Juan levanta `cassandra1` y espera a que aparezca `UN`.
2. El dueño de `cassandra2` levanta su nodo y espera a que `cassandra1` y `cassandra2` aparezcan `UN`.
3. Yo soy el último: levanto `cassandra3` solo cuando los otros dos ya estén `UN`.

Si arrancamos a la vez puede salir `Bootstrap Token collision`. La causa es el arranque no secuencial; hay que detener el proceso y repetir la secuencia, no arrancar los nodos simultáneamente.

Mi arranque:

```bash
docker compose up -d
```

La semilla solo es el punto inicial de encuentro para que un nodo se presente. Después, los nodos intercambian membresía por gossip entre pares; por eso, si `cassandra1` se cae después de que el clúster se formó, `cassandra2` y `cassandra3` todavía conocen el clúster y pueden coordinar lecturas/escrituras según el nivel de consistencia. La semilla no es un controlador ni un punto único de operación.

### Paso 5 / E1: clúster completo

Tomo la captura cuando mi nodo está `UN`, aparecen los tres nodos `UN` en `dc-g1`, y el nombre es `UFM-G1`:

```bash
docker exec cassandra3 nodetool status
docker exec cassandra3 nodetool describecluster
```

### Paso 6 / E2: tres copias

Yo no creo el keyspace ni cargo el CSV. Eso lo hace una sola vez quien tiene `cassandra1`. Cuando termine la carga, verifico desde mi nodo:

```bash
docker exec cassandra3 nodetool getendpoints ventas ventas_por_ciudad Quetzaltenango
docker exec cassandra3 cqlsh -e "DESCRIBE KEYSPACE ventas;"
```

La captura debe mostrar tres direcciones y `NetworkTopologyStrategy` con `dc-g1: '3'`.

### Paso 7 / E3: upsert, TTL e IF NOT EXISTS

Uso mi carné `20240449` como `id_venta`, en fechas de enero de 2025. Desde mi nodo:

```bash
docker exec -it cassandra3 cqlsh
```

```sql
INSERT INTO ventas.ventas_por_ciudad
  (ciudad, fecha, id_venta, pais, categoria, producto, cantidad, precio_unitario, canal)
VALUES
  ('Quetzaltenango', '2025-01-01', 20240449, 'Guatemala', 'Alimentos', 'Cafe', 1, 95.00, 'web');

INSERT INTO ventas.ventas_por_ciudad
  (ciudad, fecha, id_venta, pais, categoria, producto, cantidad, precio_unitario, canal)
VALUES
  ('Quetzaltenango', '2025-01-01', 20240449, 'Guatemala', 'Alimentos', 'Miel', 2, 100.00, 'app');

SELECT ciudad, fecha, id_venta, producto, cantidad, precio_unitario, canal
FROM ventas.ventas_por_ciudad
WHERE ciudad = 'Quetzaltenango' AND fecha = '2025-01-01' AND id_venta = 20240449;

INSERT INTO ventas.ventas_por_ciudad
  (ciudad, fecha, id_venta, pais, producto, cantidad, precio_unitario, canal)
USING TTL 60
VALUES
  ('Quetzaltenango', '2025-01-02', 20240449, 'Guatemala', 'Cafe', 3, 95.00, 'web');

SELECT id_venta, producto, TTL(producto)
FROM ventas.ventas_por_ciudad
WHERE ciudad = 'Quetzaltenango' AND fecha = '2025-01-02' AND id_venta = 20240449;
```

Espero al menos 60 segundos y repito el último `SELECT`; debe devolver `(0 rows)`. Luego pruebo la transacción ligera sobre la llave del upsert:

```sql
INSERT INTO ventas.ventas_por_ciudad
  (ciudad, fecha, id_venta, pais, producto, cantidad, precio_unitario, canal)
IF NOT EXISTS
VALUES
  ('Quetzaltenango', '2025-01-01', 20240449, 'Guatemala', 'Chocolate', 9, 50.00, 'tienda');
```

Debe mostrar `[applied] False` y la fila que ya existía. La captura E3 debe contener una sola fila para el upsert, el TTL antes y después, y ese `False`.

### Paso 8.1 / E4: un nodo caído

Como soy `cassandra3`, se apaga `cassandra1` en la laptop de Juan. Mi nodo nunca se apaga:

```bash
docker exec cassandra3 nodetool status
docker exec -it cassandra3 cqlsh
```

```sql
CONSISTENCY QUORUM;
SELECT count(*) FROM ventas.ventas_por_ciudad
WHERE ciudad = 'Quetzaltenango' AND fecha = '2024-08-01';

CONSISTENCY ALL;
SELECT count(*) FROM ventas.ventas_por_ciudad
WHERE ciudad = 'Quetzaltenango' AND fecha = '2024-08-01';
```

La captura E4 debe mostrar `cassandra1` en `DN`, `QUORUM` respondiendo y `ALL` rechazado.

### Paso 8.2 / E5: dos nodos caídos

Como soy `cassandra3`, se apagan `cassandra1` y `cassandra2`. Mi nodo sigue encendido:

```bash
docker exec cassandra3 nodetool status
docker exec -it cassandra3 cqlsh
```

```sql
CONSISTENCY ONE;
SELECT count(*) FROM ventas.ventas_por_ciudad
WHERE ciudad = 'Quetzaltenango' AND fecha = '2024-08-01';

CONSISTENCY QUORUM;
SELECT count(*) FROM ventas.ventas_por_ciudad
WHERE ciudad = 'Quetzaltenango' AND fecha = '2024-08-01';
```

La captura E5 debe mostrar dos nodos `DN`, `ONE` respondiendo y `QUORUM` rechazado. Al terminar la ronda, se vuelven a encender los nodos apagados.

### Paso 8.3: tabla de consistencia

Completar la tabla de la bitácora con `ONE`, `QUORUM` y `ALL` en los escenarios de 0, 1 y 2 nodos caídos. Al final deben quedar los tres nodos encendidos. No olvidar que el coordinador puede ser mi `cassandra3`, pero el nivel decide cuántas copias deben responder.

### Paso 9 / E6a y E6b: hinted handoff

Para este paso, por mi fila se apaga `cassandra1`; `cassandra3` nunca se apaga. Primero, Juan ejecuta en su laptop:

```bash
docker compose stop cassandra1
```

Cuando mi `nodetool status` muestre `cassandra1` en `DN`, escribo desde mi nodo usando mi carné como `id_venta`:

```bash
docker exec cassandra3 cqlsh -e "CONSISTENCY QUORUM; INSERT INTO ventas.ventas_por_ciudad (ciudad, fecha, id_venta, pais, producto, cantidad, precio_unitario, canal) VALUES ('Quetzaltenango', '2025-12-31', 20240449, 'Guatemala', 'Cafe', 3, 95.00, 'web');"
```

Espero 10 segundos y tomo E6a con:

```bash
docker exec cassandra3 ls /var/lib/cassandra/hints
docker exec cassandra3 nodetool status
```

El nombre del archivo `.hints` debe llevar el Host ID de la fila `DN`.

Juan vuelve a encender su nodo:

```bash
docker compose start cassandra1
```

Después de unos 30 segundos tomo E6b con el log y la lectura dirigida a la IP de la laptop que volvió, que en este caso es la IP de Juan/cassandra1:

```bash
docker logs cassandra3 2>&1 | grep "Finished hinted handoff"
docker exec cassandra3 cqlsh 100.71.193.83 -e "CONSISTENCY ONE; SELECT id_venta, producto, cantidad FROM ventas.ventas_por_ciudad WHERE ciudad = 'Quetzaltenango' AND fecha = '2025-12-31';"
```

El log `Finished hinted handoff` prueba que el coordinador entregó el hint al nodo que volvió; la segunda orden lee la venta directamente desde ese nodo.

## Errores probables al unir las laptops

| Síntoma | Revisión según la guía |
|---|---|
| `Saved cluster name Test Cluster != configured name UFM-G1` | Ejecutar antes de todo `docker compose down -v`; el volumen conserva datos de la Parte 1. |
| `Bootstrap Token collision` | El arranque no fue secuencial. Levantar `cassandra1`, esperar `UN`, luego `cassandra2`, esperar `UN`, y por último `cassandra3`. |
| Un contenedor se detiene solo | Revisar `docker compose logs cassandra3`; la última línea con `ERROR` indica la causa. En otra laptop se revisa el nodo de esa laptop. |
| `port is already allocated` | Revisar `lsof -nP -iTCP:7000 -sTCP:LISTEN` y el puerto 9042. En macOS, 7000 puede ser `ControlCenter` por AirPlay Receiver. |
| Los nodos no se ven o `NoHostAvailable` | Confirmar mismo tailnet, peers Tailscale visibles, IPs `100.x.x.x` alcanzables, firewall TCP 7000/9042, `CASSANDRA_BROADCAST_ADDRESS` propio y `CASSANDRA_SEEDS` apuntando a Juan. |
| La semilla aparece como destino incorrecto | `CASSANDRA_SEEDS` debe ser `100.71.193.83`, la IP Tailscale de `cassandra1`, nunca la IP propia de `cassandra3`. |
| Cluster o datacenter incompatibles | Los tres deben usar `UFM-G1` y `dc-g1`; el keyspace del Paso 6 debe usar exactamente `NetworkTopologyStrategy` con `'dc-g1': 3`. |
| `ALL` o `QUORUM` devuelve `Unavailable` durante las pruebas | Es el resultado esperado cuando no hay suficientes réplicas vivas; revisar que se esté ejecutando desde `cassandra3` y que la ronda corresponda al número de nodos caídos. |
| No aparece el archivo `.hints` | Esperar al menos 10 segundos y confirmar que el nodo estaba en `DN` antes de escribir. |
| No aparece `Finished hinted handoff` | Esperar a que el nodo vuelto llegue a `UN` y repetir el `grep`; la guía indica que la entrega ocurre después del arranque. |
| La lectura final no encuentra la venta | Usar `cqlsh 100.71.193.83` contra la IP Tailscale de `cassandra1` que volvió y comprobar que el `id_venta` usado fue `20240449`. |

## Limpieza posterior

Solo después de terminar bitácora, mini-reto y presentación:

```bash
docker compose down -v
```

Esto elimina los contenedores y volúmenes del taller, no otros datos.
