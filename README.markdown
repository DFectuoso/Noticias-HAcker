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

Para modificar el css requieres compilar los archivos scss con [sass](http://sass-lang.com/)

Estado actual:
--------------

El codigo esta funcionando en [Noticias Hacker](http://noticiashacker.com) y aunque no esta perfectamente optimizado, esta consumiendo pocos recursos en el app engine y ha aguantado muchos usuarios de golpe(20k visitas en 24 horas gracias a un post en HN).
Aun asi, seria bueno idea seguir optimizandolo para que funciona tan rapido como sea posible, aunque esto es un reto en el app engine, se puede conseguir si seguimos usando memcache para todo lo que sea posible y tratar de hacer operaciones agrupadas cuando se pueda.

Las cosas que tenemos que trabajar en los proximos dias y semanas son:

* Mensajes de error al registrarse
* Mensajes de error al entregar nuevas noticias
* Agregar una manera de recuperar el password(despues de poner tu correo en el perfil)
* Agregar la posibilidad de que los usuarios editen sus propios post
* Agregar una manera de moderar/editar/borrar mensajes y comentarios
* Agregar un api publico 
* Seguir mejorando el estilo


