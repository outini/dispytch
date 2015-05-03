#! /usr/bin/env bash

#
# Use this script to test your dispatcher without webservice
#

# REQUEST_METHOD may be one of the following:
#   GET     Simulate GET request, REQUEST_URI and DOCUMENT_PATH are required
#   POST    Simulate POST request, dispatcher stdin will receive data
# If not defined, dispatcher will assume commandline call

export REQUEST_METHOD="GET"

export DOCUMENT_PATH="/munin/by-ip/1.1.1.1/cpu/AVERAGE/now-2w/now"
export DOCUMENT_PATH="/munin/by-id/clientA;test;hostA/cpu/AVERAGE/now-2w/now"
export REQUEST_URI="$DOCUMENT_PATH"
python ./dispytch/__init__.py

#export DOCUMENT_PATH="/munin/list"
#export REQUEST_URI="/munin/list"
#python ./dispytch/__init__.py

#export DOCUMENT_PATH="/info"
#export REQUEST_URI="/info"
#python ./dispytch/__init__.py
