import requests
import re
import json
import time
import pickle

def getSteamUserGameList(steamid):
    """Se conecta a la pagina del perfil del usuario 'steamid'
    de http://steamcommunity.com/profiles/
    y descarga la lista de todos los juegos que tiene el usuario.
    Si el perfil es privado o no tiene juegos return None
    """
    print("probando usuario", steamid, end="... ")
    steamurl = "http://steamcommunity.com/profiles/"+str(steamid)+"/games/?tab=all"

    # HTTP request al perfil de steam del usuario 'steamid'
    res = requests.get(steamurl)
    res.raise_for_status()
    
    # el html descargado tiene una variable "rgGames" que contiene la lista de todos los juegos
    # del usuario en formato JSON. Se busca y se extrae la lista con una expresion regular
    #
    # !! usar expresiones regulares en html no es una buena idea... pero funciona
    # LEER: https://stackoverflow.com/questions/1732348/regex-match-open-tags-except-xhtml-self-contained-tags
    gameListJson=re.findall(r'.*var rgGames = (.*);', res.text)

    # si el perfil es privado, no hay variable rgGames
    if not gameListJson:
        print("! El perfil es privado, se ignora")
        return None

    # deserializar JSON a un diccionario de python
    gameList = json.loads(gameListJson[0]) # diccionario de diccionarios

    # si el usuario no tiene juegos se ignora
    if not gameList:
        print("! El usuario no tiene juegos, se ignora")
        return None

    print("el usuario tiene", len(gameList), "juegos")
        
    return(gameList)


def getGameTags(gameid):
    """Cada juego de steam tiene asociado un 'gameid'.
    Desde la pagina de https://steamspy.com/ descarga
    los metadatos del juego 'gameid' y devuelve los 'tags' del juego
    """
    print("     descargando informacion del juego", gameid, end="... ")
    steamspyurl = "http://steamspy.com/api.php?request=appdetails&appid="+str(gameid)

    # HTTP request a la API que ofrece https://steamspy.com/
    res = requests.get(steamspyurl)
    res.raise_for_status()

    # el resultado es un JSON con los metadatos del juego 'gameid'
    # ejemplo del juego 'Half-Life 2':
    # http://steamspy.com/api.php?request=appdetails&appid=220
    gameInfoJson = res.text
    # de JSON a diccionario de python
    gameInfo = json.loads(gameInfoJson)

    print(gameInfo["name"])

    # de todos los metadatos solo nos interesan los 'tags' del juego
    return(gameInfo["tags"])


# Cada usuario de steam tiene asociado un numero de identificacion
# los steamID se asignan de un modo secuencial empezando desde el
# numero 76561197960265728
steamIdMinNumber = 76561197960265728+1

# En esta lista se ponen todos los steamID-s que se quieran analizar con
# este programa
uidList = range(steamIdMinNumber+1000, steamIdMinNumber+1500) # <- Modificar esto a gusto

# de los usuarios de uidList no todos van a ser procesados porque hay
# perfiles privados y otros que no tienen juegos. Los usuarios validos
# se van a guardar en la lista totalUsers
totalUsers = list()

# De todos los 'tags' diferentes que existen en Steam, solo se van
# a procesar los 'tags' que aparezcan en esta lista
allTags = ["Indie", "Action", "Adventure", "Strategy", "Simulation",
           "RPG", "Free to Play", "Early Access", "Massively Multiplayer",
           "Sports", "Violent", "Racing", "Multiplayer", "Singleplayer", "Gore",
           "Puzzle", "Horror", "Shooter", "FPS", "First-Person", "Survival", "Difficult",
           "Rogue-like", "Platformer", "Turn-Based Strategy", "Psychological Horror",
           "Action RPG", "RTS", "MMORPG", "JRPG", "Zombies"]

# Cada juego de Steam puede tener un numero indefinido de tags,
# si un juego tiene mas de maxTagPerGame tags la lista de tags
# se va a cortar para que tenga la longitud maxTagPerGame.
# Los tags estan ordenados de mayor importancia a menor,
# 10 tags son mas que suficientes.
maxTagPerGame = 10

# Despues de hacer un request el programa se duerme para no hacer spam
# se definen los segundos para dormir aqui
steamSleep = 6
steamspySleep = 1

cnt = 1

# Cada vez que se descargan los metadatos de un juego al final se añaden a un
# archivo 'tagdb.pickle' para que la siguiente vez que se ejecute el programa
# no tenga que descargar de nuevo los mismos datos de juegos que ya ha procesado.
# Esto es importante para que no este constantemente haciendo requests a la pagina de
# steamspy y nos bloqueen el acceso.
try:
    f = open("tagdb.pickle", "rb")
    gameTagDb = pickle.load(f)
    f.close()
except FileNotFoundError:
    # Si el archivo no existe, se empieza de cero
    gameTagDb = dict()

### Empezar a procesar ###
for uid in uidList:
    print(">>> [", cnt, "/", len(uidList), "]", end=" ") #progreso

    # evitar spam a Steam para que no nos bloqueen el acceso
    if cnt%20 == 0:
        time.sleep(60)
        
    gameList = getSteamUserGameList(uid)
    
    if not gameList:
        time.sleep(steamSleep)
        cnt += 1
        continue

    # histograma en el que se va a guardar para cada usuario el conteo de tags
    hist = {"uid":uid, "nJuegos":len(gameList)}
    gcnt = 1
    
    for game in gameList:
        print("     (", gcnt, "/", len(gameList), ")", end=" ") #progreso
        if game["appid"] in gameTagDb:
            print("     el juego", game["name"], "esta en la base de datos")
            downloadedTags = gameTagDb[game["appid"]]
            time.sleep(0.01)
        else:
            time.sleep(steamspySleep)
            downloadedTags = getGameTags(game["appid"])
            gameTagDb[game["appid"]] = downloadedTags
            print("     se añade el juego", game["name"], "a la base de datos")
        
        tagList = list(downloadedTags)
        if len(tagList) > maxTagPerGame:
            tagList = tagList[0:maxTagPerGame]

        for tag in tagList:
            if tag in allTags:
                hist[tag] = hist.get(tag, 0)+1
    
        gcnt += 1
        # evitar spam a steamspy para que no nos bloqueen el acceso
        if gcnt%50 == 0:
            time.sleep(10)

    totalUsers.append(hist)
    cnt += 1
    time.sleep(steamSleep)
    

# Guardar la base de datos de tags descargados
f = open("tagdb.pickle", "wb")
pickle.dump(gameTagDb, f, pickle.HIGHEST_PROTOCOL)
f.close()

# Guardar los datos procesados como csv
f = open("steamtagsOK_new1000-1500.csv", "w") # <- No olvidarse de poner nombre que no exista!
header = "steamid,nJuegos,"
for tag in allTags:
    header += tag+","

f.write(header[:-1]+"\n")

for user in totalUsers:
    line = str(user.get("uid"))+","+str(user.get("nJuegos"))+","
    for tag in allTags:
        line += str(user.get(tag, 0))+","
    f.write(line[:-1]+"\n")
f.close()
