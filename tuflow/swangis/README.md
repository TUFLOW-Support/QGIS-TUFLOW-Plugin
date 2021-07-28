## SWANGIS
SWANGIS (Simulating WAves Nearshore in Geographic Information Systems) is a QGIS plugin for setting up SWAN models. 
The goal of SWANGIS is to make the complex procedure of setting up SWAN models simple with visualization and 
automation.

## Installing
To install, download the SWANGIS package from the gitlab [repository](https://gitlab.com/TUFLOW/swangis) and copy the 
contents of %USERPROFILE%\Downloads\swangis\swangis\ to %USERPROFILE%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\swangis.
QGIS will then know where the package\plugin is located and execute it on startup.

## Dependencies
SWANGIS depends on the following packages: 

```
GDAL==3.1.1
matplotlib==3.2.1
netCDF4==1.5.4
numpy==1.18.4
PyQt5==5.14.2
requests==2.24.0
scipy==1.4.1
```

## Use Outside of QGIS
Most of this package is developed outside of QGIS, and can be used outside of QGIS. When used outside of QGIS, because
the package isn't available on the Python Package Index (PyPi), the dependencies must be manually installed.

First, download this wheel GDAL-3.1.3-cp37-cp37m-win_amd64.whl from [here](www.lfd.uci.edu/gohlke/pythonlibs) 

Once the wheel has been downloaded, install the GDAL bindings via the windows command prompt:

```
python -m pip install .\PATH\TO\YOUR\WHEEL\GDAL-3.1.1-cp37-cp37m-win_amd64.whl 
```

Next, install the additional requirements via the windows command prompt:

```
python -m pip install -r .\PATH\TO\YOUR\REQUIREMENTS\requirements.txt 
```
  
Next, copy the contents of .\swangis\ to .\PATH\TO\YOUR\PYTHON\ENVIRONMENT\Lib\site-packages\swangis\


## Authors
* **Jonah Chorley (BMT)**