# API REST for the Drone Engineeging Ecosystem

## Introduction
The APIREST module is responsible for storing data on the ground and retrieving it as requested by the rest of the ecosystem modules. The module offers a RESTful interface, so that any module can access the data through HTTP requests (GET, POST, PUT, DELETE). Therefore, the communication between APIREST and the rest of modules is not implemented via MQTT, but via HTTP. The data is stored in a MongoDB database.   
      
As an example, the user can design a flightplan using some of the front-end modules of the ecosystem and store it in the APIREST module. Later, the user can retrieve the flight plan and sent it to the autoplilot to be executed. In the event that the flightplan includes the taking of photos or videos, these can also be stored in the database and recoveren by the front-end module to be shown to the user.   


## Requirements
Before starting with the installation, make sure you have the following software installed on your system:

- Python 3.7
- MongoDB Community Edition
- MongoDB Database Tools
- MongoDB Compass (optional, but recommended for easier database management)
- PyCharm (or any preferred IDE)

You can install MongoDB and MongoDB Database Tools from the following links:
- [Install MongoDB](https://www.mongodb.com/docs/manual/administration/install-community/)
- [Install MongoDB Database Tools](https://www.mongodb.com/docs/database-tools/)

To make it easier to work with the database, it is also recommended to install [MongoDB Compass](https://www.mongodb.com/products/compass).


## Installation and set up
To run and contribute, clone this repository to your local machine and install the requirements.  
    
To run the APIREST in localhost for simulation you must edit the run/debug configuration in PyCharm, as shown in the image, in order to pass the required arguments to the script. 
You will need to change from Script path to Module name and input _uvicorn_, as well as adding the following parameters: _main:app --reload_.
![image](https://github.com/Frixon21/RestApiDEE/assets/72676967/e34bd344-ee58-4d86-b2ba-dc65c5d5c117)
![image](https://github.com/Frixon21/RestApiDEE/assets/72676967/d8c9e3e4-b2a8-4df5-be1f-376d070fe58d)


To restore the database you will have to run the following command from the main RestApi dirrectory. Keep in mind that if you did not add the mongoDB Tools to your path you will have to copy them into your folder. 
```
mongorestore dump/
```

## Endpoints and data models
Once the service has started, navigate to http://127.0.0.1:8000 to see and try all the different API endpoints.
![image](https://github.com/Frixon21/RestApiDEE/assets/72676967/a9c89fcc-6552-4918-9f06-bdd76c7cfa29)

You will see easily the data models involved in the different API endpoints (for instance the data model for a flight plan).    

## Tutorial
This is a tutorial  (in Spanish) to learn how to install the APIREST and create (and test) new ednpoints:
    
[Tutorial on APIREST](https://www.youtube.com/playlist?list=PLyAtSQhMsD4o3VIWiQ7xYB9dx7f-C8Ju1)      
     



