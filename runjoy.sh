#!/bin/bash
# My first script

pigpiod
cd flystick-futaba-tm-hotas
git pull
python pifly.py
