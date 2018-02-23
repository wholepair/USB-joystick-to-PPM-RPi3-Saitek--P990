#!/bin/bash
# Start PiFly

pigpiod
python pifly.py &
cd -
