# elcaBonsai
Importwerkezeug für Projekt- und Ergebnissdateien des [BBSR Bauteileditors](https://www.bauteileditor.de) in [Bonsai](bonsai.org) 


## Überblick
Ermöglicht den Import von Projekt- und Ergebnissdateien des BBSR Bauteileditors in Bonsai. Dieses Werkzeug ist nützlich für die Integration von Bauteildaten in die Bonsai-Plattform.


## Funktionen
- Laden von Projektdateien  
- Laden von Massenbilanzen gespeichtet als HTML Seite  
- Erzeugung und Import von IFC-Materialen und Materialien-Gruppen (IfcMaterial und IfcMaterialLayerSet) mit Ökobaudat Referenzierung

## Voraussetzungen
- [Bonsai](https://bonsai.org) Version 0.8.3
- Kostenlosen Login für den BBSR [Bauteileditor](https://bauteleditor.de)


## Installation
Installation des elcaBonsai-Werkzeugs erfolgt das Blender-Addon System. 
Die jeweils letzte Verion kann aus dem Release-Ordner des [elcaBonsai GitHub Repositories](https://github.com/jakob-beetz/elcaBonsai/releases/latest) als .zip Datei heruntergeladen werden.

![](img/elca_addon_install_screen.png)

Wenn das Addon installiert ist, finden sich die beiden folgenden neuen Buttons im Material-Panel von IFC Projekten:
![](img/ecla_addon_in_material_panel.png)    


## Schnellstart
Im Reiter „**Geometry and Materials**“ können aus heruntergeladenen eLCA-Projektdateien über das Panel „**eLCA Integration**“ IFC-Libraries erzeugt werden.

Im Reiter „**Project Overview**“ kann die IFC-Library unter „**Project Setup > Project Library**“ als Custom Library importiert werden, aus der einzelne Materialien dem Projekt hinzugefügt werden können.

Zurück im Reiter „**Geometry and Materials**“ können den ausgewählten Elementen im Panel „**Object Materials**“ die neu hinzugefügten Materialien zugewiesen werden.


## Dokumentation

## Beispiele


## Mitwirken
Pull Requests und Fehlermeldungen sind sehr willkommen


## Lizenz

LGPL v 3.0, matching Bonsai license

## Kontakt und Hilfe
- Fragen, Vorschläge und Fehlermeldungen für elcaBonsai hier im Forum.
- Für Fragen und Unterstützung wenden Sie sich bitte an die Bonsai-Community oder besuchen Sie die [Bonsai-Website](https://bonsai.org).

## Förderung
Das Werkzeug ist Teil einer Serie von Prototypen im Rahmen des Forschungs-Projektes [BIM-basierte Ökobilanzierung](https://www.zukunftbau.de/projekte/forschungsfoerderung/1008187-2429), geförderte durch das [ZukunftBau](https://www.zukunftbau.de/) Programm des [Bundesinstituts für Bau-, Stadt- und Raumforschung (BBSR)](https://www.bbsr.bund.de/).