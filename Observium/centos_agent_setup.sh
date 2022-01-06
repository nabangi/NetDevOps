#!/usr/bin/env bash
# Author : Alvaro Nabangi
# CONFIG
SNMP_COMMUNITY=public
SYSCONTACT=monitor@yourdomain.com
SYSLOCATION=Africa/Nairobi

# get packages
yum install wget snmpd xinetd nano -y

mkdir -p /opt/observium && cd /opt

wget http://www.observium.org/observium-community-latest.tar.gz --no-check-certificate
tar zxvf observium-community-latest.tar.gz

sed -e "/SNMPDOPTS=/ s/^#*/SNMPDOPTS='-Lsd -Lf \/dev\/null -u snmp -p \/var\/run\/snmpd.pid'\n#/" -i /etc/default/snmpd

wget http://www.observium.org/svn/observer/trunk/scripts/distro
mv distro /usr/bin/distro
chmod 755 /usr/bin/distro

mv /etc/snmp/snmpd.conf /etc/snmp/snmpd.conf.org
cat >/etc/snmp/snmpd.conf <<EOL
com2sec readonly  default         $SNMP_COMMUNITY
group MyROGroup v1         readonly
group MyROGroup v2c        readonly
group MyROGroup usm        readonly
view all    included  .1                               80
access MyROGroup ""      any       noauth    exact  all    none   none
syslocation $SYSLOCATION
syscontact $SYSCONTACT
#This line allows Observium to detect the host OS if the distro script is installed
extend .1.3.6.1.4.1.2021.7890.1 distro /usr/bin/distro 
EOL


cp observium/scripts/observium_agent_xinetd /etc/xinetd.d/observium_agent

# confirm the "port", "protocol" and change "only_from" to match your observium server ip
nano /etc/xinetd.d/observium_agent

cp observium/scripts/observium_agent /usr/bin/observium_agent

mkdir -p /usr/lib/observium_agent/local

# copy all agent helper scripts that you want (bind, dpkg, freeradius, ksm, munin, mysql.cnf, ntpd, postfix_qshape, powerdns, rpm, shoutcast.conf, unbound, apache, crashplan, drbd, hddtemp, lmsensors, munin-scripts, nfs, nvidia-smi, postgresql.conf, powerdns-recursor, sabnzbd-qstatus, shoutcast.default.conf, vmwaretools, asterisk, dmi, exim-mailqueue.sh, ipmitool-sensor, memcached, mysql, nginx, postfix_mailgraph, postgresql.pl, raspberrypi, shoutcast, temperature)
# to make this work you have to enable the unix-agent module on your device's settings or globally in config.php ($config['poller_modules']['unix-agent'] = 1;)
cp observium/scripts/agent-local/AGENTHELPER /usr/lib/observium_agent/local/

yum install libvirt.x86_64

systemctl restart xinetd
systemctl restart snmpd
systemctl enable snmpd
