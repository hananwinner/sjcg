syncano_java_class_generator

Generate Java class for Syncano class

positional arguments:
  API-KEY             The API-KEY used to retrieve class metadata.
  CLASSES-URL         Full URL to the Syncano classes endpoint.
  DESTINATION-FOLDER  Folder path to create the Java classes at.
  PACKAGE             Java package to create the classes at.

optional arguments:
  -h, --help          show this help message and exit
  
Will get the list of classes from Syncano, And create/override Java Class Files in the destination folder. 

Overriding
Does not propmpt before overriding.
Will skip if the class in the folder is not a @SyncanoClass.

