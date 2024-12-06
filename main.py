from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, constr
import json
#-------------- API EXTERNA -------------------
# Importar las librerías externas de Spotify
from dotenv import load_dotenv  
import os
import requests 
import base64
import time


app = FastAPI(
    title="API de Usuarios y Música (Spotify)",
    description="Esta API gestiona usuarios y sus preferencias musicales, y también permite obtener información desde Spotify.",
    version="1.0.0"
)

# Modelo de datos del usuario (ModelUser)
class ModelUser(BaseModel):
    name: str
    email: EmailStr  # Esto valida que el correo tenga el formato adecuado (ej. usuario@dominio.com)

#Modelo de datos para spotify
class SongRequest(BaseModel):
    nombre_cancion: str

class ArtistRequest(BaseModel):
    nombre_artista: str



# Para cargar y guardar en archivo JSON
def load_base_users():
    try:
        with open("users.json", "r") as file:
            data = json.load(file)
            # Convertir las claves de string a enteros
            return {int(key): value for key, value in data.items()}
    except FileNotFoundError:
        return {}  # Si el archivo no existe, devolvemos un diccionario vacío

def save_base_users(base_users):
    with open("users.json", "w") as file:
        json.dump(base_users, file, indent=4)

# CREAR USUARIO = POST
@app.post("/api/users/")
def create_data_user(data_user: ModelUser):  
    base_users = load_base_users()  # Cargamos los usuarios actuales del archivo JSON

    # Comprobamos si ya existe un usuario con el mismo nombre y email
    for existing_user in base_users.values():  # Recorremos los usuarios existentes
        if existing_user["name"] == data_user.name and existing_user["email"] == data_user.email:
            raise HTTPException(status_code=400, detail={"error": "El usuario con ese nombre y email ya existe"})

    # Validamos que el nombre y el email no estén vacíos
    if not data_user.name or not data_user.email:  # Si el nombre o el email están vacíos
        raise HTTPException(status_code=400, detail={"error": "Se necesita un nombre y un email válidos"})

    # Generar un nuevo ID automáticamente
    new_id = max(base_users.keys(), default=0) + 1
    # Crear el usuario con el nuevo ID
    base_users[new_id] = {"id": new_id, "name": data_user.name, "email": data_user.email}

    save_base_users(base_users)  # Guardamos el diccionario actualizado en el archivo JSON
    #return base_users[new_id]  # Devolvemos el usuario creado
    return {"user": base_users[new_id]}  # Devolver el usuario dentro de un diccionario con una clave 'user'

# LEER BASE DE DATOS DE USUARIOS = GET
@app.get("/api/users/")
def get_base_users():
    base_users = load_base_users()  # Cargamos los usuarios actuales del archivo JSON
    #return base_users  # Devolvemos todos los usuarios
    return {"users": base_users}  # Asegúrate de envolver en un diccionario

# LEER BASE DE DATOS DE USUARIO CONCRETO = GET
@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    base_users = load_base_users()  # Cargamos los usuarios actuales del archivo JSON
    # Verificamos si el usuario existe
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="El usuario no existe")
    
    # Retornamos los datos del usuario específico
    return {"user": base_users[user_id]}


# ACTUALIZAR USUARIO = PUT
@app.put("/api/users/{user_id}")
def update_data_user(user_id: int, data_user: ModelUser):
    base_users = load_base_users()  # Cargamos los usuarios actuales del archivo JSON
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")  # Si el usuario no existe, lanzamos una excepción

    base_users[user_id] = data_user.dict()  # Actualizamos el usuario con el nuevo contenido
    save_base_users(base_users)  # Guardamos el archivo JSON actualizado
    #return base_users[user_id]  # Devolvemos el usuario actualizado
    return {"user": base_users[user_id]}

# ELIMINAR USUARIO = DELETE
@app.delete("/api/users/{user_id}")
def delete_data_user(user_id: int):
    base_users = load_base_users()  # Cargamos los usuarios desde el archivo JSON
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")  # Si el usuario no existe, lanzamos un error 404

    del base_users[user_id]  # Eliminamos al usuario por su ID

    # Reordenar los IDs para que sean consecutivos
    reordered_base_users = {}
    for new_id, user in enumerate(base_users.values(), start=1):
        user["id"] = new_id  # Actualizamos el ID del usuario
        reordered_base_users[new_id] = user

    save_base_users(reordered_base_users)  # Guardamos los usuarios reordenados en el diccionario

    return {"detail": "Usuario eliminado correctamente"}




#<------- SPOTIFY FLUJO CLIENT CREDENTIAL-------->
    
# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Recuperar las credenciales de Spotify
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


# Variable global para almacenar el token de acceso y su tiempo de expiración
access_token = None
token_expiration_time = None

def obtener_token_spotify():
    global access_token, token_expiration_time
    
    # Si ya tenemos un token y no ha expirado, retornamos el token existente
    if access_token and time.time() < token_expiration_time:
        return access_token
    
    # Si no tenemos token o ha expirado, obtenemos uno nuevo
    url = "https://accounts.spotify.com/api/token"
    
    # Codificar las credenciales en Base64
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    credentials_base64 = base64.b64encode(credentials.encode()).decode()

    # Configurar las cabeceras para la solicitud POST
    headers = {
        "Authorization": f"Basic {credentials_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # Configurar los datos que se enviarán en el cuerpo de la solicitud
    data = {
        "grant_type": "client_credentials"
    }

    
#<----- SPOTIFY OBTENER TOKEN ------>

    # Hacer la solicitud POST para obtener el token
    response = requests.post(url, headers=headers, data=data)

    # Comprobar si la solicitud fue exitosa
    if response.status_code == 200:
        # Extraer el token de la respuesta
        data = response.json()
        access_token = data.get("access_token")
        
        # Obtener el tiempo de expiración del token (en segundos)
        expires_in = data.get("expires_in", 3600)  # Si no se encuentra, por defecto es 3600 segundos (1 hora)
        token_expiration_time = time.time() + expires_in  # Establecer el tiempo de expiración
        
        return access_token
    else:
        # Si algo salió mal, lanzar una excepción
        raise HTTPException(status_code=400, detail="No se pudo obtener el token de Spotify")





# Función para obtener un artista de Spotify por nombre
def buscar_artista_spotify(nombre_artista):
    url = f"https://api.spotify.com/v1/search?q={nombre_artista}&type=artist&limit=1"
    response = requests.get(url, headers={"Authorization": f"Bearer {obtener_token_spotify()}"})

    if response.status_code == 200:
        data = response.json()
        artista = data['artists']['items'][0] if data['artists']['items'] else None
        if artista:
            return {
                "id": artista['id'],
                "name": artista['name'],
                "url": artista['external_urls']['spotify'],
            }
    return None

# Función para obtener una canción de Spotify por nombre
def buscar_cancion_spotify(nombre_cancion):
    url = f"https://api.spotify.com/v1/search?q={nombre_cancion}&type=track&limit=1"
    response = requests.get(url, headers={"Authorization": f"Bearer {obtener_token_spotify()}"})

    if response.status_code == 200:
        data = response.json()
        cancion = data['tracks']['items'][0] if data['tracks']['items'] else None
        if cancion:
            return {
                "id": cancion['id'],
                "titulo": cancion['name'],
                "artista": cancion['artists'][0]['name'],
                "url": cancion['external_urls']['spotify'],
            }
    return None



# <---- Endpoint para agregar un artista favorito al usuario por nombre ----->
@app.post("/api/users/{user_id}/add-favorite-artist")
def agregar_artista_favorito(user_id: int, artist_request: ArtistRequest):
    base_users = load_base_users()

    # Verificamos que el usuario exista
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="El usuario no existe")

    # Buscamos el artista en Spotify usando su nombre
    artista = buscar_artista_spotify(artist_request.nombre_artista)

    if not artista:
        raise HTTPException(status_code=404, detail="El artista no se encontró en Spotify")

    # Si el usuario no tiene una lista de artistas favoritos, la creamos
    if 'spotify_artists' not in base_users[user_id]:
        base_users[user_id]['spotify_artists'] = []

    # Verificamos si el artista ya está en la lista de favoritos
    for existing_artist in base_users[user_id]['spotify_artists']:
        if existing_artist['id'] == artista['id']:
            raise HTTPException(status_code=400, detail=f"El artista {artista['name']} ya está en la lista de favoritos")

    # Añadimos el artista a la lista de favoritos
    base_users[user_id]['spotify_artists'].append(artista)

    # Guardamos los cambios en el archivo JSON
    save_base_users(base_users)

    return {
        "detail": f"El artista {artista['name']} ha sido agregado a favoritos",
        "user": base_users[user_id]  # Devolvemos los datos actualizados del usuario
    }


# <----- Endpoint para agregar una canción favorita al usuario por nombre ----->

@app.post("/api/users/{user_id}/add-favorite-song")
def agregar_cancion_favorita(user_id: int, song_request: SongRequest):
    base_users = load_base_users()  # Cargamos los usuarios actuales del archivo JSON

    # Verificamos que el usuario exista
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="El usuario no existe")

    # Ahora podemos acceder al nombre de la canción desde request.nombre_cancion
    nombre_cancion = song_request.nombre_cancion

    # Buscamos la canción en Spotify usando su nombre
    cancion = buscar_cancion_spotify(nombre_cancion)

    if not cancion:
        raise HTTPException(status_code=404, detail="La canción no se encontró en Spotify")

    # Si el usuario no tiene una lista de canciones favoritas, la creamos
    if 'spotify_songs' not in base_users[user_id]:
        base_users[user_id]['spotify_songs'] = []

    # Verificamos si la canción ya está en la lista de favoritos
    for existing_song in base_users[user_id]['spotify_songs']:
        if existing_song['id'] == cancion['id']:
            raise HTTPException(status_code=400, detail=f"La canción {cancion['titulo']} ya está en la lista de favoritos")

    # Añadimos la canción a la lista de favoritos
    base_users[user_id]['spotify_songs'].append(cancion)

    # Guardamos los cambios en el archivo JSON
    save_base_users(base_users)

    return {
        "detail": f"La canción {cancion['titulo']} ha sido agregada a favoritos",
        "user": base_users[user_id]  # Devolvemos los datos actualizados del usuario
    }

#<---- Endpoint consultar artista en spotify ----->
@app.get("/api/spotify/artist-info/")
def obtener_informacion_artista(nombre_artista: str):
    # Buscar el artista por nombre
    artista = buscar_artista_spotify(nombre_artista)
    if not artista:
        raise HTTPException(status_code=404, detail="El artista no se encontró en Spotify")

    # Obtener el top de canciones del artista
    url_top_tracks = f"https://api.spotify.com/v1/artists/{artista['id']}/top-tracks?market=US"
    response_top_tracks = requests.get(url_top_tracks, headers={"Authorization": f"Bearer {obtener_token_spotify()}"})

    if response_top_tracks.status_code == 200:
        top_tracks_data = response_top_tracks.json()
        top_tracks = [track["name"] for track in top_tracks_data.get("tracks", [])[:5]]  # Limitar a los nombres de las 5 canciones más populares
    else:
        raise HTTPException(status_code=400, detail="No se pudieron obtener las canciones populares del artista")

    return {
        "nombre": artista["name"],
        "popularidad": artista.get("popularity", "No disponible"),
        "url": artista["url"],
        "top_5_canciones": top_tracks  # Lista de solo nombres
    }


#<--- Endpoint obtener información sobre una canción ---->
@app.get("/api/spotify/song-info/")
def obtener_informacion_cancion(nombre_cancion: str):
    # Buscar la canción por nombre
    cancion = buscar_cancion_spotify(nombre_cancion)
    if not cancion:
        raise HTTPException(status_code=404, detail="La canción no se encontró en Spotify")

    return {
        "titulo": cancion["titulo"],
        "artista": cancion["artista"],
        "url": cancion["url"],
        "popularidad": cancion.get("popularity", "No disponible")
    }






# <----- Endpoint para obtener los artistas favoritos del usuario -----> 
@app.get("/api/users/{user_id}/favorite-artists")
def obtener_artistas_favoritos_del_usuario(user_id: int):
    base_users = load_base_users()  # Cargamos los usuarios actuales del archivo JSON

    # Verificamos que el usuario exista
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Verificamos si el usuario tiene artistas favoritos
    if 'spotify_artists' not in base_users[user_id]:
        raise HTTPException(status_code=404, detail="El usuario no tiene artistas favoritos")

    # Devolvemos los artistas favoritos del usuario
    return {
        "user_id": user_id,
        "artistas_favoritos": base_users[user_id]["spotify_artists"]
    }



# <------ Obtener las canciones favoritas del usuario -------->
@app.get("/api/users/{user_id}/favorite-songs")
def obtener_canciones_favoritas_del_usuario(user_id: int):
    base_users = load_base_users()  # Cargamos los usuarios actuales del archivo JSON

    # Verificamos que el usuario exista
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Verificamos si el usuario tiene canciones favoritas
    if 'spotify_songs' not in base_users[user_id]:
        raise HTTPException(status_code=404, detail="El usuario no tiene canciones favoritas")

    # Devolvemos las canciones favoritas del usuario
    return {
        "user_id": user_id,
        "canciones_favoritas": base_users[user_id]["spotify_songs"]
    }






# <------ Eliminar un artista favorito del usuario ------>

@app.delete("/api/users/{user_id}/delete-favorite-artist")
def eliminar_artista_favorito(user_id: int, artist_request: ArtistRequest):
    base_users = load_base_users()  # Cargamos los usuarios actuales del archivo JSON

    # Verificar si el usuario existe
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Verificar si tiene una lista de artistas favoritos
    if 'spotify_artists' not in base_users[user_id]:
        raise HTTPException(status_code=404, detail="El usuario no tiene artistas favoritos")

    # Buscar el artista por nombre en la lista de favoritos
    artista = next((artist for artist in base_users[user_id]['spotify_artists'] if artist['name'] == artist_request.nombre_artista), None)
    
    if not artista:
        raise HTTPException(status_code=404, detail="El artista no está en la lista de favoritos")

    # Eliminar el artista de la lista
    base_users[user_id]['spotify_artists'].remove(artista)

    # Guardar los cambios en el archivo JSON
    save_base_users(base_users)

    return {
        "detail": f"Artista {artista['name']} eliminado de la lista de favoritos",
        "user": base_users[user_id]  # Devolver el usuario actualizado
    }


# <------ Eliminar una canción favorita del usuario ------>
@app.delete("/api/users/{user_id}/delete-favorite-song")
def eliminar_cancion_favorita(user_id: int, song_request: SongRequest):
    base_users = load_base_users()  # Cargamos los usuarios actuales del archivo JSON

    # Verificar si el usuario existe
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Verificar si tiene una lista de canciones favoritas
    if 'spotify_songs' not in base_users[user_id]:
        raise HTTPException(status_code=404, detail="El usuario no tiene canciones favoritas")

    # Buscar la canción por nombre en la lista de favoritos
    cancion = next((song for song in base_users[user_id]['spotify_songs'] if song['titulo'] == song_request.nombre_cancion), None)

    if not cancion:
        raise HTTPException(status_code=404, detail="La canción no está en la lista de favoritos")

    # Eliminar la canción de la lista
    base_users[user_id]['spotify_songs'].remove(cancion)

    # Guardar los cambios en el archivo JSON
    save_base_users(base_users)

    return {
        "detail": f"Canción {cancion['titulo']} eliminada de la lista de favoritos",
        "user": base_users[user_id]  # Devolver el usuario actualizado
    }