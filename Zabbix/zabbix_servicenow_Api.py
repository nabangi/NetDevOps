#!/usr/bin/python
#import zapi
from pyzabbix.api import ZabbixAPI
import datetime
import sys
import urllib2
import os
import requests
#import redis
from servicenow import ServiceNow
from servicenow import Connection
#import servicenow.Connection
#import servicenow.ServiceNow

##
## I've used logging for my own setup, but I've commented it out so that it 
won't spam a log file unless you uncomment it.
## Just make sure the location that you're storing the logfile is writable by 
the zabbix user
## In this example, I've used /usr/lib/zabbix/logfiles but this could be 
anywhere writable by the zabbix user
#f = open('/usr/lib/zabbix/logfiles/snow.log','a')
#f.write('\n\nScript Start :: '+datetime.datetime.now().ctime()+'\n\n')
#f.write(','.join(sys.argv)+'\n')

## Zabbix Passes the details via command line arguments.
print(sys.argv, len(sys.argv))
assignmentgroup = sys.argv[1:]
description = sys.argv[2:]
detail = sys.argv[3:]

## Set Up your Zabbix details
zabbixsrv = "localhost"
zabbixun = "username"
zabbixpw = "password"

## Set up your ServiceNow instance details
## For Dublin+ instances, connect using JSONv2, otherwise use JSON
username = "edsu"
password = "bele"
instance = "servicenowsubdomain"
api = "JSONv2"

## I've configured Zabbix to only pass the Event ID in the message body.
## If you want more detail in the body of the incident in ServiceNow, you'll 
need to make sure that eventid is parsed out of detail correctly.
eventid = detail

#f.write('trying to connect to servicenow\n')
try:
        conn = 
servicenow.Connection.Auth(username=username,password=password,instance=instance
, api=api)
except:
        print ("Error Connecting to ServiceNow\n")
#f.write("Error Connecting to ServiceNow\n")

#f.write('trying to create incident instance\n')
try:
        inc = servicenow.ServiceNow.Incident(conn)
except:
        print ("Error creating incident instance\n")
#f.write("Error creating incident instance\n")

#f.write('trying to create new incident\n')

## This is where the fun starts.
## You'll need to set up the following section with the correct form fields, as 
well as the default values
try:
        newinc = servicenow.ServiceNow.Incident.create(inc, { \
"short_description":description, \
"description":detail, \
"priority":"3", \
"u_requestor":"autoalert", \
"u_contact_type":"Auto Monitoring", \
"assignment_group": assignmentgroup})
#f.write("\n\n"+str(newinc)+"\n\n")
except Exception as e:
        print ("Error creating new incident in ServiceNow\n")
#f.write("Error creating new incident in ServiceNow\n")
#f.write(str(e)+"\n")

## This script will retrieve the new incident number from servicenow and put it 
back into zabbix as an acknowledgement
try:
        newincno = newinc["records"][0]["number"]
except:
        print ("unable to retrieve new incident number\n")
#f.write("unable to retrieve new incident number\n")

zapi = 
ZabbixAPI(url='http://'+zabbixsrv+'/zabbix',user=zabbixun,password=zabbixpw)
#zapi.user.login()
#f.write('Acknowledging event '+eventid+'\n')
#zapi.Event.acknowledge({'eventids':[eventid],'message':newincno})

# Get all monitored hosts
result1 = zapi.host.get(monitored_hosts=1, output='extend')
# Get all disabled hosts
result2 = zapi.do_request('host.get',
                              {
                                  'filter': {'status': 1},
                                  'output': 'extend'
                              })

# Filter results
hostnames1 = [host['host'] for host in result1]
hostnames2 = [host['host'] for host in result2['result']]

# Logout from Zabbix
zapi.user.logout()

#f.write('\n\nScript End :: '+datetime.datetime.now().ctime()+'\n\n')
#f.close()
