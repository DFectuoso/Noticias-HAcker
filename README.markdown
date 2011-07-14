Noticias Hacker
===============

Este es un clon de hacker news con la intencion de tener un servicio similar para Iberoamerica y demas personas que hablen castellano.

Instalacion
-----------

* Instalar el Google App Engine SDK
* Agregar este repositorio como un proyecto existente
* Crear un archivo llamado "keys.py". Este archivo contiene un hash para saltear los password y otros para la session. Este archivo debe de tener las siguientes dos lineas:

cookie_key = 'UNASTRINGALEATORIAMUYLARGAUNASTRINGALEATORIAMUYLARGAUNASTRINGALEATORIAMUYLARGA'

salt_key = 'UNASTRINGALEATORIAMUYLARGA'

Si quisieras usar el bot de twitter tambien necesitarias agregar las siguientes llaves de la misma manera:

consumer_key = ""

consumer_secret = ""

access_token = ""

access_token_secret = ""

bitly_login = ''

bitly_apikey = ''

base_url = '' # Esto es para que solo funcione en el dominio adecuado y no en el sitio de pruebas

base_url_custom_url = '' # Esto es si tienes un dominio diferente a appspot

CSS
---

Para modificar el css requieres compilar los archivos scss con [sass](http://sass-lang.com/)

Estado actual:
--------------

El codigo esta funcionando en [Noticias Hacker](http://noticiashacker.com) y aunque no esta perfectamente optimizado, esta consumiendo pocos recursos en el app engine y ha aguantado muchos usuarios de golpe(20k visitas en 24 horas gracias a un post en HN).
Aun asi, seria bueno idea seguir optimizandolo para que funciona tan rapido como sea posible, aunque esto es un reto en el app engine, se puede conseguir si seguimos usando memcache para todo lo que sea posible y tratar de hacer operaciones agrupadas cuando se pueda.

Las cosas que tenemos que trabajar en los proximos dias y semanas son:

* Agregar una manera de recuperar el password(despues de poner tu correo en el perfil)
* Agregar una manera de borrar mensajes y comentarios
* Agregar un api publico 
* Seguir mejorando el estilo

