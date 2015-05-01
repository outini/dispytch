#! /usr/bin/env bash

#
# Use this script to test your dispatcher without webservice
#

# REQUEST_METHOD may be one of the following:
#   GET     Simulate GET request, REQUEST_URI and DOCUMENT_PATH are required
#   POST    Simulate POST request, dispatcher stdin will receive data
# If not defined, dispatcher will assume commandline call

export REQUEST_METHOD="GET"

export REQUEST_URI="/api.munin/by-ip/1.1.1.1/cpu/AVERAGE/now-2h/now"
export DOCUMENT_PATH="$REQUEST_URI"

# It is assumed you runned this script from the repository root
python ./dispytch/__init__.py
