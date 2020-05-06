#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

case "$OSTYPE" in
    solaris*) ;;
    darwin*)  ln -s $DIR/tuflow ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/tuflow ;;
    linux*)   ln -s $DIR/tuflow ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/tuflow  ;;
    bsd*)     ;;
    msys*)    ;;
    *)        ;;
esac
