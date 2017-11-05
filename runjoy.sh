#!/bin/bash
# Start PiFly

pigpiod
cd flystick-futaba-tm-hotas
git pull &> /dev/null
python pifly.py &
cd -
